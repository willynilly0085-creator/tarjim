"""The integration review of the translation rounds (2026-11-08): an engine that cannot be built
hands over to the backup, one failed batch never abandons the batches after it, a used-up quota
or a timed-out engine in a second ask stops the engine and says why, and the stop note names only
the engine that ran last."""
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import pipeline
from tarjim.engines import choice
from tarjim.engines.web import TimedOut
from tarjim.findings import FINDINGS, Findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES


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


def engines(monkeypatch: pytest.MonkeyPatch, **askers: Answers | Exception) -> None:
    def build(provider: str) -> Answers:
        made = askers[provider]
        if isinstance(made, Exception):
            raise made
        return made

    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", build)


def one(text: str) -> list[dict[str, Any]]:
    return [{"id": 1, "text": text}]


def kinds(found: Findings, cues: list[Cue]) -> list[str]:
    return [row["kind"] for row in found.notes(cues, [])]


def test_an_engine_that_cannot_be_built_hands_over_to_the_backup(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    backup = Answers(one("Bonjour."))
    engines(monkeypatch, gemini=RuntimeError("Gemini API key missing"), local=backup)
    done = pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
    assert done[0].text == "Bonjour." and len(backup.prompts) == 1
    assert found.notes(done, []) == []


def test_a_backup_that_cannot_be_built_keeps_what_the_first_engine_did(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello."), said(400.0, "Bye.")]
    chosen = Answers(one("Bonjour."), QuotaExhausted("gemini: quota used up"))
    engines(monkeypatch, gemini=chosen, local=OSError("no local model server"))
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "Bye."] and found.in_source == [2]
    stop = [row for row in found.notes(done, []) if row["kind"] == "engine_stopped"]
    assert stop and stop[0]["reason"] == "quota"  # the backup never ran: the quota is why


def test_one_failed_batch_never_abandons_the_batches_after_it(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(t, "hello there friend") for t in (0.0, 400.0, 800.0, 1200.0)]
    busy = RuntimeError("all Gemini models failed: 503")
    chosen = Answers(one("un"), busy, busy, one("trois"), one("quatre"))
    engines(monkeypatch, gemini=chosen)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["un", "hello there friend", "trois", "quatre"]
    assert len(chosen.prompts) == 5 and found.in_source == [2]
    assert "engine_stopped" in kinds(found, done)


@pytest.mark.parametrize("final", [QuotaExhausted("gemini: quota used up"),
                                   TimedOut("claude", 0, "no answer in 300 s")])
def test_a_final_error_in_the_second_ask_stops_the_engine_and_says_why(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings,
        final: Exception) -> None:
    lines = [said(0.0, "Hello."), said(2.0, "How are you?"), said(400.0, "Bye.")]
    chosen = Answers(one("Bonjour."), final, one("never asked"))
    engines(monkeypatch, gemini=chosen)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "How are you?", "Bye."]
    assert len(chosen.prompts) == 2 and found.in_source == [2, 3]
    stop = [row for row in found.notes(done, []) if row["kind"] == "engine_stopped"]
    assert stop and stop[0]["detail"] in str(final)


def test_a_final_error_while_unsliding_stops_the_engine(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    monkeypatch.setattr("tarjim.translate.gemini.slid", lambda _cues: True)
    lines = [said(0.0, "Hello."), said(400.0, "Bye.")]
    chosen = Answers(one("Bonjour."), QuotaExhausted("gemini: quota used up"))
    engines(monkeypatch, gemini=chosen)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "Bye."] and len(chosen.prompts) == 2
    assert found.stopped is not None and "quota" in str(found.stopped)


def test_a_line_the_backup_left_out_is_not_blamed_on_the_first_engines_quota(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello."), said(400.0, "Bye."), said(402.0, "See you.")]
    chosen = Answers(one("Bonjour."), QuotaExhausted("gemini: quota used up"))
    backup = Answers(one("Au revoir."), [])
    engines(monkeypatch, gemini=chosen, local=backup)
    done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "Au revoir.", "See you."]
    assert kinds(found, done) == ["in_source"]
