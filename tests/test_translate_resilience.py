"""One bad answer costs one batch at most: good lines are kept, and the backup fills only gaps."""
from pathlib import Path
from typing import Any

import pytest

from tarjim import pipeline
from tarjim.engines import choice
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.gemini import Translator, batches
from tarjim.translate.prompt import Brief


class Answers:
    hears = False

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def ask(self, prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def silence(_start: float, _end: float) -> bytes:
    return b""


def brief() -> Brief:
    return Brief(language("fr"), "", DEFAULT_RULES)


def said(start: float, text: str) -> Cue:
    return Cue(start, start + 1.0, [Word(text, start, start + 1.0)])


def dialogue() -> Cue:
    first, second = [Word("Once.", 0.0, 0.5, "S1")], [Word("Yeah?", 0.6, 1.0, "S2")]
    return Cue(0.0, 1.0, first + second, parts=[first, second])


def test_a_failed_batch_is_asked_once_more_on_the_same_engine() -> None:
    engine = Answers(RuntimeError("503 busy"), [{"id": 1, "text": "Bonjour."}])
    done = Translator(engine).translate([said(0, "Hello.")], silence, brief())
    assert [c.text for c in done] == ["Bonjour."]


def test_a_failed_second_pass_keeps_what_the_first_pass_filled() -> None:
    cue = dialogue()
    engine = Answers([{"id": 1, "text": "Une fois."}], RuntimeError("503 busy"))
    Translator(engine).translate([cue], silence, brief())
    assert cue.text == "Une fois."


def test_the_second_pass_never_empties_a_good_line() -> None:
    cue = dialogue()
    engine = Answers([{"id": 1, "text": "Une fois."}], [{"id": 1, "text": "  "}])
    Translator(engine).translate([cue], silence, brief())
    assert cue.text == "Une fois."


def test_a_batch_of_only_sounds_may_come_back_empty() -> None:
    sounds = [said(0, "Mm."), said(2, "Hmm.")]
    engine = Answers([{"id": 1, "text": ""}, {"id": 2, "text": ""}], [])
    done = Translator(engine).translate(sounds, silence, brief())
    assert [c.text for c in done] == ["", ""]


def test_the_backup_engine_fills_only_the_lines_still_empty(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    job: Any = type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                                "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()
    lines = [said(0, "Hello."), said(400, "Bye.")]
    chosen = Answers([{"id": 1, "text": "Bonjour."}], RuntimeError("503"), RuntimeError("503"))
    backup = Answers([{"id": 1, "text": "Au revoir."}])
    askers = {"gemini": chosen, "local": backup}
    monkeypatch.setattr(choice, "chain", lambda _task: ["gemini", "local"])
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])
    done = pipeline.translate(job, lines)
    assert [c.text for c in done] == ["Bonjour.", "Au revoir."]
    assert len(backup.prompts) == 1 and "Hello." not in backup.prompts[0]


def test_local_engines_get_small_batches() -> None:
    lines = [said(t * 2.0, "Hi.") for t in range(100)]
    assert max(len(b) for b in batches(lines)) == 100
    assert max(len(b) for b in batches(lines, most=40)) == 40
    assert sum(len(b) for b in batches(lines, most=40)) == 100
