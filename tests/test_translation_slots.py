"""Every translated slot is checked, a failing one is asked again beside its neighbours, then of
the next engine, and a line no engine translated still shows the words as they were said."""
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import pipeline
from tarjim.engines import choice
from tarjim.findings import FINDINGS, Findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief


class Answers:
    def __init__(self, *answers: Any, hears: bool = False) -> None:
        self.answers, self.hears = list(answers), hears
        self.prompts: list[str] = []
        self.sounds: list[bytes | None] = []

    def ask(self, prompt: str, audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        self.sounds.append(audio)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def found() -> Iterator[Findings]:
    """The job's record, put back as it was after the test."""
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


def said(start: float, text: str, speaker: str = "") -> Cue:
    return Cue(start, start + 1.5, [Word(text, start, start + 1.5, speaker)])


def exchange(speakers: tuple[str, str] = ("", "")) -> Cue:
    first, second = [Word("Once.", 0.0, 0.5, speakers[0])], [Word("Yeah?", 0.6, 1.0, speakers[1])]
    return Cue(0.0, 1.0, first + second, parts=[first, second])


def shortening() -> Any:
    from tarjim.prefs.active import using
    from tarjim.prefs.model import resolve

    return using(resolve({"translate.shorten": True}, {}, "fr"))


def brief() -> Brief:
    return Brief(language("fr"), "", DEFAULT_RULES)


def sound(start: float, end: float) -> bytes:
    return f"{start:.1f}-{end:.1f}".encode()


def job(tmp_path: Path) -> Any:
    return type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                            "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()


def engines(monkeypatch: pytest.MonkeyPatch, **askers: Answers) -> None:
    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])


def test_a_dropped_slot_is_asked_again_alone_beside_its_neighbours_with_the_same_sound() -> None:
    lines = [said(t * 2.0, f"Line {t}.") for t in range(7)]
    first = [{"id": n, "text": f"Ligne {n - 1}."} for n in range(1, 8) if n != 4]
    engine = Answers(first, [{"id": 1, "text": "Ligne 3."}], hears=True)
    Translator(engine).translate(lines, sound, brief())
    assert lines[3].text == "Ligne 3."
    again = engine.prompts[1]
    assert "for all 1 slots" in again and "Line 3." in again
    assert "- Line 0. => Ligne 0." in again and "- Line 6. => Ligne 6." in again
    assert engine.sounds[0] == engine.sounds[1]


@pytest.mark.parametrize("answer", ["Une || fois || oui", "Une fois. || "])
def test_an_exchange_with_the_wrong_parts_is_cleared_and_asked_again(answer: str) -> None:
    cue = exchange()
    engine = Answers([{"id": 1, "text": answer}], [{"id": 1, "text": "Une fois. || Ah oui ?"}])
    Translator(engine).translate([cue], sound, brief())
    assert cue.text == "Une fois. || Ah oui ?" and len(engine.prompts) == 2


def test_an_exchange_answered_as_one_sentence_is_one_speaker() -> None:
    cue = exchange()
    engine = Answers([{"id": 1, "text": "Une fois, oui ?"}])
    Translator(engine).translate([cue], sound, brief())
    assert cue.text == "Une fois, oui ?" and len(engine.prompts) == 1
    assert not cue.is_dialogue and cue.parts == [cue.words]


def test_one_speaker_split_in_two_is_joined_back() -> None:
    cue = said(0.0, "Hello there.")
    Translator(Answers([{"id": 1, "text": "Bonjour || là."}])).translate([cue], sound, brief())
    assert cue.text == "Bonjour là."


def test_a_sound_answered_empty_is_not_asked_again() -> None:
    lines = [said(0.0, "Mm-hmm."), said(2.0, "Hello.")]
    engine = Answers([{"id": 1, "text": ""}, {"id": 2, "text": "Bonjour."}])
    Translator(engine).translate(lines, sound, brief())
    assert [c.text for c in lines] == ["", "Bonjour."] and len(engine.prompts) == 1


def test_a_line_the_first_engine_left_empty_goes_to_the_backup(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    lines = [said(0.0, "Hello."), said(2.0, "How are you today?")]
    chosen = Answers([{"id": 1, "text": "Bonjour."}], [{"id": 1, "text": ""}])
    backup = Answers([{"id": 1, "text": "Comment vas-tu ?"}])
    engines(monkeypatch, gemini=chosen, local=backup)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "Comment vas-tu ?"]
    assert "How are you today?" in backup.prompts[0] and "- Hello. => Bonjour." in backup.prompts[0]


def test_a_used_up_backup_keeps_the_first_engines_lines_and_shows_the_rest_as_said(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello."), said(2.0, "今日は本当にありがとうございました")]
    chosen = Answers([{"id": 1, "text": "Bonjour."}], [{"id": 1, "text": ""}])
    engines(monkeypatch, gemini=chosen, local=Answers(QuotaExhausted("quota used up")))
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "今日は本当にありがとうございました"]
    assert found.in_source == [2]


@pytest.mark.usefixtures("found")
def test_an_exchange_no_engine_translated_is_shown_as_said_in_its_two_parts(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    lines = [said(5.0, "Hello."), exchange()]
    chosen = Answers([{"id": 1, "text": "Bonjour."}], [{"id": 1, "text": "Une || fois || oui"}])
    engines(monkeypatch, gemini=chosen)
    done = pipeline.translate(job(tmp_path), lines)
    assert done[1].text == "Once. || Yeah?"


LONG = "Une traduction bien trop longue pour une seule seconde et demie, et même pour trois"


def test_a_line_too_long_for_its_time_is_asked_for_once_more_shorter(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    """2026-11-12: for a person who turned it on; nothing is ever shortened otherwise."""
    chosen = Answers([{"id": 1, "text": LONG}], [{"id": 1, "text": "Bonjour à tous."}])
    engines(monkeypatch, gemini=chosen, local=Answers())
    with shortening():
        done = pipeline.translate(job(tmp_path), [said(0.0, "Hello there.")])
    assert done[0].text == "Bonjour à tous." and found.over_budget == []
    assert len(chosen.prompts) == 2 and "limit" in chosen.prompts[1]
    assert LONG in chosen.prompts[1] and "Hello there." in chosen.prompts[1]


@pytest.mark.parametrize("second", [[{"id": 1, "text": LONG + " encore"}], [{"id": 1, "text": ""}],
                                    RuntimeError("busy"), [{"id": 1, "text": "Un || deux"}]])
def test_a_shorter_answer_that_does_not_fit_leaves_the_line_and_lists_it(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings, second: Any) -> None:
    chosen = Answers([{"id": 1, "text": LONG}], second)
    engines(monkeypatch, gemini=chosen, local=Answers())
    with shortening():
        done = pipeline.translate(job(tmp_path), [said(0.0, "Hello there.")])
    assert done[0].text == LONG and found.over_budget == [1] and found.in_source == []
    assert len(chosen.prompts) == 2


def test_a_long_line_stays_up_into_the_silence_after_it_before_any_word_changes(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    fits_in_three = "Une phrase qui se lit en trois secondes"
    chosen = Answers([{"id": 1, "text": fits_in_three}, {"id": 2, "text": "Oui."}])
    engines(monkeypatch, gemini=chosen, local=Answers())
    cues = [said(0.0, "A sentence read in three seconds."), said(10.0, "Yes.")]
    done = pipeline.translate(job(tmp_path), cues)
    assert done[0].text == fits_in_three and len(chosen.prompts) == 1  # no word changed
    assert 2.2 < done[0].end <= 3.5 and found.over_budget == []
    assert done[1].end == 11.5  # a line that fits keeps its time


def test_a_line_never_stays_onto_the_next_one_or_past_a_cut_of_the_picture() -> None:
    from tarjim.translate import readable

    crowded = [said(0.0, "a"), said(1.6, "b")]
    crowded[0].text = crowded[1].text = "x" * 60
    readable.given_time(crowded, DEFAULT_RULES, [])
    assert crowded[0].end <= 1.6 - DEFAULT_RULES.min_gap + 1e-6
    cut = [said(0.0, "a")]
    cut[0].text = "x" * 60
    readable.given_time(cut, DEFAULT_RULES, [2.0])
    assert 1.5 < cut[0].end <= 2.0 - DEFAULT_RULES.min_gap + 1e-6


def test_nothing_is_asked_for_shorter_unless_the_person_turned_it_on(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    """The owner, 2026-11-12: no shortening at all, accuracy first."""
    chosen = Answers([{"id": 1, "text": LONG}])
    engines(monkeypatch, gemini=chosen, local=Answers())
    done = pipeline.translate(job(tmp_path), [said(0.0, "Hello there.")])
    assert done[0].text == LONG and len(chosen.prompts) == 1 and found.over_budget == [1]


def test_a_full_translation_is_asked_to_leave_nothing_out_and_is_never_shortened(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    from tarjim.prefs.active import using
    from tarjim.prefs.model import resolve

    chosen = Answers([{"id": 1, "text": LONG}])
    engines(monkeypatch, gemini=chosen, local=Answers())
    with using(resolve({"translate.length": "full", "translate.shorten": True}, {}, "fr")):
        done = pipeline.translate(job(tmp_path), [said(0.0, "Hello there.")])
    asked = chosen.prompts[0]
    assert "never condense or leave out" in asked and "Fillers alone" in asked
    assert "Never exceed" not in asked and "shorten that slot" not in asked
    assert done[0].text == LONG and len(chosen.prompts) == 1 and found.over_budget == [1]


def test_the_usual_prompt_is_word_for_word_what_it_was() -> None:
    from tarjim.translate.prompt import build_prompt

    asked = build_prompt([said(0.0, "Hello there.")], brief())
    assert "- Never exceed the slot's character budget: condense and drop fillers" in asked
    assert "shorten that slot's own translation; never carry the rest into the next slot." in asked


def test_no_engine_answering_at_all_still_fails_the_job_with_its_reason(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engines(monkeypatch, gemini=Answers(QuotaExhausted("gemini: quota used up")),
            local=Answers(RuntimeError("busy"), RuntimeError("busy")))
    with pytest.raises(QuotaExhausted, match="quota"):
        pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
