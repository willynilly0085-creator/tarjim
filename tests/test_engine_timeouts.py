"""An engine whose requests run out of time, or that keeps failing, hands over (2026-11-08).

Before, a requests timeout reached the translation as a plain engine error, so every batch of a
long clip waited twice: on a local model on the processor that is hours before the job fails or
the backup is tried. Now a timeout is final (web.TimedOut), and an engine that failed two batches
in a row is asked no more.
"""
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import requests

from tarjim import pipeline
from tarjim.engines import choice, web
from tarjim.findings import FINDINGS, Findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief


class Posting:
    """An engine that asks through the real web.post, whose requests.post raises `error`."""
    hears = False
    most_cues = 40  # like the local model: small batches

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.asks = 0

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.asks += 1
        with mock.patch("requests.post", side_effect=self.error):
            return web.post("local", "http://127.0.0.1:11434/api/chat", {}, json={})


class Fine:
    hears = False

    def __init__(self) -> None:
        self.asks = 0

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.asks += 1
        return [{"id": n, "text": "bonjour"} for n in range(1, 401)]  # extra ids are ignored


@pytest.fixture
def found() -> Iterator[Findings]:
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


def clip(minutes: int) -> list[Cue]:
    return [Cue(t, t + 1.5, [Word("hello there", t, t + 1.5)]) for t in range(0, minutes * 60, 3)]


def run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, **askers: Any) -> list[Cue]:
    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])
    job = type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                           "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()
    return pipeline.translate(job, clip(20))


@pytest.mark.parametrize("error", [requests.exceptions.ReadTimeout("Read timed out."),
                                   requests.exceptions.ConnectTimeout("connect timed out")])
def test_a_requests_timeout_is_final(error: Exception) -> None:
    with mock.patch("requests.post", side_effect=error), pytest.raises(web.TimedOut):
        web.post("local", "http://127.0.0.1:11434/api/chat", {}, json={})


def test_a_timed_out_engine_is_not_asked_batch_after_batch(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    slow = Posting(requests.exceptions.ReadTimeout("Read timed out. (read timeout=300)"))
    with pytest.raises(web.TimedOut, match="timed out"):  # nothing translated: the job fails
        run(monkeypatch, tmp_path, local=slow)
    assert slow.asks <= 2


def test_a_timed_out_engine_hands_over_to_the_backup_at_once(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    slow = Posting(requests.exceptions.ReadTimeout("Read timed out. (read timeout=300)"))
    backup = Fine()
    done = run(monkeypatch, tmp_path, local=slow, gemini=backup)
    assert slow.asks == 1 and all(cue.text == "bonjour" for cue in done)
    assert found.in_source == []


def test_an_engine_failing_two_batches_in_a_row_hands_over_to_the_backup(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    gone = Posting(requests.exceptions.ConnectionError("connection refused"))
    backup = Fine()
    done = run(monkeypatch, tmp_path, local=gone, gemini=backup)
    assert gone.asks == 4  # two batches, each asked twice
    assert all(cue.text == "bonjour" for cue in done) and found.in_source == []


class Then:
    hears = False

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_an_exchange_answered_as_one_sentence_is_one_speaker_when_unsliding_stops(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tarjim.translate.gemini.slid", lambda _cues: True)
    first, second = [Word("Once.", 0.0, 0.5)], [Word("Yeah?", 0.6, 1.0)]
    cue = Cue(0.0, 1.0, first + second, parts=[first, second])
    engine = Then([{"id": 1, "text": "Une fois, oui ?"}], QuotaExhausted("quota used up"))
    with pytest.raises(QuotaExhausted):
        Translator(engine).translate([cue], lambda _s, _e: b"", Brief(language("fr"), "",
                                                                       DEFAULT_RULES))
    assert cue.text == "Une fois, oui ?" and cue.parts == [cue.words]
