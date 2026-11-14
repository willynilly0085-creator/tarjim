"""What a translated line is measured against (2026-11-08): an exchange part by part against the
budgets its prompt gave, and a line of only fillers or laughter is a sound in any spelling."""
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import pipeline
from tarjim.engines import choice
from tarjim.findings import FINDINGS, Findings
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.prompt import Brief, build_prompt
from tarjim.translate.slots import only_a_sound

SOUNDS = ["Ha ha ha ha", "Hahahaha", "Ha ha!", "hehehe", "Uh, um.", "Oh, oh.", "Hm hm",
          "Hmm, hmm", "Ah ah ah", "Whoa", "Whoooa!", "Ugh", "Ugh, uh", "Mm-hmm, mm-hmm."]
WORDS = ["Oh no", "Uh, yes.", "Ha ha, very funny", "He", "Hi", "Hello", "Ohio", "Hehe what?",
         "Ha, no."]


class Answers:
    hears = False

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def ask(self, prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        return self.answers.pop(0)


@pytest.fixture
def found() -> Iterator[Findings]:
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


def job(tmp_path: Path) -> Any:
    return type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                            "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()


def exchange(seconds: float, speakers: tuple[str, str] = ("S1", "S2")) -> Cue:
    half = seconds / 2
    first = [Word("Where were you all day?", 0.0, half, speakers[0])]
    second = [Word("At the market, why?", half, seconds, speakers[1])]
    return Cue(0.0, seconds, first + second, parts=[first, second])


def engines(monkeypatch: pytest.MonkeyPatch, **askers: Answers) -> None:
    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])


def answered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cue: Cue, text: str) -> None:
    engines(monkeypatch, gemini=Answers([{"id": 1, "text": text}]))
    pipeline.translate(job(tmp_path), [cue])


@pytest.mark.parametrize("seconds", [1.0, 2.0, 4.0])
def test_an_exchange_that_keeps_each_part_budget_is_not_listed_as_too_long(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings, seconds: float) -> None:
    first, second = DEFAULT_RULES.budgets(seconds, 2)
    answered(monkeypatch, tmp_path, exchange(seconds), f"{'a' * first} || {'b' * second}")
    assert found.over_budget == []


def test_an_exchange_part_over_its_own_budget_is_listed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    first, _second = DEFAULT_RULES.budgets(2.0, 2)
    answered(monkeypatch, tmp_path, exchange(2.0), f"{'a' * (first + 3)} || b")
    assert found.over_budget == [1]


def test_one_sentence_for_a_guessed_exchange_may_use_the_sum_of_its_parts(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    whole = sum(DEFAULT_RULES.budgets(1.0, 2))
    answered(monkeypatch, tmp_path, exchange(1.0, ("", "")), "a" * whole)
    assert found.over_budget == []


@pytest.mark.parametrize("target", ["ar", "fr"])
def test_the_prompt_says_a_split_budget_is_a_limit_for_each_part(target: str) -> None:
    from tarjim.prefs.model import resolve

    fitted = resolve({"translate.length": "fit"}, {}, target).translate
    prompt = build_prompt([exchange(2.0)],
                          Brief(language(target), "saudi", DEFAULT_RULES, manner=fitted))
    assert "budget=" in prompt and "a+b" in prompt


@pytest.mark.parametrize("text", SOUNDS)
def test_fillers_and_laughter_in_any_spelling_are_a_sound(text: str) -> None:
    assert only_a_sound(text)


@pytest.mark.parametrize("text", WORDS)
def test_a_line_with_one_real_word_is_not_a_sound(text: str) -> None:
    assert not only_a_sound(text)


def test_repeated_fillers_never_start_the_backup_engine(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [Cue(t, t + 1.5, [Word(text, t, t + 1.5)])
             for t, text in [(0.0, "Hello."), (2.0, "Hmm, hmm"), (4.0, "Ha ha ha ha")]]
    chosen = Answers([{"id": 1, "text": "Bonjour."}, {"id": 2, "text": ""},
                      {"id": 3, "text": ""}])
    backup = Answers()
    engines(monkeypatch, gemini=chosen, local=backup)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "", ""]
    assert len(chosen.prompts) == 1 and backup.prompts == []
    assert found.in_source == [] and found.sounds == [2, 3]
