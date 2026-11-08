"""The review of the slot checks (2026-11-08): an empty answer for a short real line in any
language or script is a failure and goes to the backup; only a fixed list of fillers may be left
empty, and they are still counted on the job; an engine that stopped partway says why; and the
timing check of a kept transcript is shown again on a re-run."""
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import hearing, pipeline
from tarjim.asr.base import Transcript
from tarjim.engines import choice
from tarjim.findings import FINDINGS, Findings, findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.job import Job
from tarjim.languages import language
from tarjim.listen.kept import TRANSCRIPT
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.slots import only_a_sound

SHORT_WORDS = ["No.", "Yes.", "Why?", "Run!", "Hi", "نعم", "لا", "هم", "Да", "Нет", "А", "Er",
               "أم", "ام",
               "नहीं", "हम", "是的", "不是", "谢谢", "待って", "行こう", "はい", "いいえ", "うん",
               "아니요", "어", "Oui", "Non", "Ja"]
FILLERS = ["Mm-hmm.", "Hmm...", "Uh", "Um,", "uh huh", "Mmm", "嗯", "えー", "うーん", "ممم",
           "آه", "Хм", "음", "Euh"]


class Answers:
    def __init__(self, *answers: Any) -> None:
        self.answers, self.hears = list(answers), False
        self.prompts: list[str] = []

    def ask(self, prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def found() -> Iterator[Findings]:
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


def said(start: float, text: str) -> Cue:
    return Cue(start, start + 1.5, [Word(text, start, start + 1.5)])


def job(tmp_path: Path) -> Any:
    return type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                            "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()


def engines(monkeypatch: pytest.MonkeyPatch, **askers: Answers) -> None:
    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])


@pytest.mark.parametrize("word", SHORT_WORDS)
def test_a_short_real_line_is_never_taken_for_a_sound(word: str) -> None:
    assert not only_a_sound(word)


@pytest.mark.parametrize("filler", FILLERS)
def test_a_filler_is_a_sound_in_any_script(filler: str) -> None:
    assert only_a_sound(filler)


@pytest.mark.parametrize("word", ["No.", "是的", "はい", "Нет"])
def test_a_short_line_answered_empty_is_asked_again_then_of_the_backup(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings, word: str) -> None:
    lines = [said(0.0, "Are you coming?"), said(2.0, word)]
    chosen = Answers([{"id": 1, "text": "Tu viens ?"}, {"id": 2, "text": ""}],
                     [{"id": 1, "text": ""}])
    backup = Answers([{"id": 1, "text": "Non."}])
    engines(monkeypatch, gemini=chosen, local=backup)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Tu viens ?", "Non."]
    assert len(chosen.prompts) == 2 and len(backup.prompts) == 1
    assert found.sounds == [] and found.in_source == []


def test_a_short_line_no_engine_translated_is_shown_as_said_and_listed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Are you coming?"), said(2.0, "No.")]
    chosen = Answers([{"id": 1, "text": "Tu viens ?"}, {"id": 2, "text": ""}],
                     [{"id": 1, "text": ""}])
    engines(monkeypatch, gemini=chosen, local=Answers([{"id": 1, "text": ""}]))
    done = pipeline.translate(job(tmp_path), lines)
    assert done[1].text == "No." and found.in_source == [2]
    assert [n["kind"] for n in found.notes(done, [])] == ["in_source"]


def test_a_filler_left_empty_is_not_asked_again_but_counted_quietly(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello."), said(2.0, "Mm-hmm.")]
    chosen = Answers([{"id": 1, "text": "Bonjour."}, {"id": 2, "text": ""}])
    engines(monkeypatch, gemini=chosen, local=Answers())
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", ""] and len(chosen.prompts) == 1
    notes = found.notes(done, [])
    assert notes == [{"kind": "sounds", "problem": False, "count": 1, "at": [2.0]}]


def test_an_engine_that_stopped_partway_says_why_on_the_job(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(t, f"Line number {n}.") for n, t in enumerate([0.0, 2.0, 400.0, 402.0])]
    chosen = Answers([{"id": 1, "text": "L0"}, {"id": 2, "text": "L1"}],
                     QuotaExhausted("gemini: quota used up for today"))
    engines(monkeypatch, gemini=chosen)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["L0", "L1", "Line number 2.", "Line number 3."]
    stopped = [n for n in found.notes(done, []) if n["kind"] == "engine_stopped"]
    assert stopped == [{"kind": "engine_stopped", "problem": True, "count": 1, "at": [],
                        "reason": "quota", "detail": "gemini: quota used up for today"}]


def test_a_backup_that_filled_every_line_leaves_no_stop_note(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello.")]
    engines(monkeypatch, gemini=Answers(QuotaExhausted("quota used up")),
            local=Answers([{"id": 1, "text": "Bonjour."}]))
    done = pipeline.translate(job(tmp_path), lines)
    assert done[0].text == "Bonjour." and found.notes(done, []) == []


def test_a_kept_transcript_brings_back_its_timing_check(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    clip = Job(tmp_path / "v.mp4")
    transcript = Transcript("English", "hi", [Word("hi", 0.0, 0.5)])
    monkeypatch.setattr(hearing, "hear", lambda *_args: (findings().heard((), 0.31) or
                                                         (transcript, True)))
    monkeypatch.setattr(hearing.media, "extract_audio", lambda *_args: None)
    monkeypatch.setattr("tarjim.memory.free_for_listening", lambda: None)
    hearing.transcript_for(clip, lambda _stage: None)
    assert (clip.cache / TRANSCRIPT).exists()
    again = Findings()
    FINDINGS.set(again)
    hearing.transcript_for(clip, lambda _stage: None)
    assert again.agreement == 0.31 and again.notes([], [])[0]["share"] == 31
