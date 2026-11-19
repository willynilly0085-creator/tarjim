"""A job translated by a model other than the one the person picked says which one did.

Found 2026-11-16: a picked Gemini model the key refused (400, 403 or 404) handed its lines to the
next model of the usual list, and only the job's log said so; the page and the extension kept
naming the picked model, so a person believed it had translated their video. The same held for a
picked Antigravity effort answered by its low variant, a Codex model the account refused, and a
chosen engine whose lines the backup translated.
"""
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, gemini_client, pipeline
from tarjim.engines import antigravity, choice, subscription
from tarjim.findings import FINDINGS, Findings
from tarjim.gemini_client import MODELS, GeminiClient, QuotaExhausted
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES

PICKED = "gemini-4-hydrogen"
pytestmark = pytest.mark.usefixtures("prefs_home")  # never the person's own saved models


class Answers:
    """An engine that answers in turn and says which of its models did, as Gemini's does."""
    hears = False

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.model_used = ""

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        model, answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        self.model_used = model
        return answer


class Refused(Exception):
    def __init__(self) -> None:
        super().__init__("404 NOT_FOUND. models/gemini-4-hydrogen is not found for API version")
        self.code = 404


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


def engines(monkeypatch: pytest.MonkeyPatch, **askers: Any) -> None:
    monkeypatch.setattr(choice, "chain", lambda _task: list(askers))
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])


def one(text: str) -> list[dict[str, Any]]:
    return [{"id": 1, "text": text}]


def swapped(found: Findings, cues: list[Cue]) -> list[dict[str, Any]]:
    return [note for note in found.notes(cues, []) if note["kind"] == "other_model"]


def gemini_refusing_the_pick() -> GeminiClient:
    """Gemini's own client, its pick refused by the key as Google answers it."""
    client = GeminiClient.__new__(GeminiClient)
    client.spent, client.model_used, client.cooling, client.refused = set(), "", {}, set()
    client.models, client.slow, client.listening = [PICKED, *MODELS], set(), False

    def call(model: str, *_: Any) -> Any:
        if model == PICKED:
            raise Refused()
        client.model_used = model
        return one("Bonjour.")

    client.call = call  # type: ignore[method-assign]
    return client


def test_a_picked_gemini_model_the_key_refused_is_named_with_the_one_that_translated(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    engines(monkeypatch, gemini=gemini_refusing_the_pick())
    with config.using({"gemini_model": PICKED}):
        done = pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
    assert done[0].text == "Bonjour."
    assert swapped(found, done) == [{"kind": "other_model", "problem": False, "count": 1,
                                     "at": [], "picked": "Gemini 4 Hydrogen",
                                     "used": ["Gemini 3.8 Flash"]}]


def test_the_picked_model_or_no_pick_at_all_says_nothing(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    engines(monkeypatch, gemini=Answers((PICKED, one("Bonjour."))))
    with config.using({"gemini_model": PICKED}):
        done = pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
    assert swapped(found, done) == []
    engines(monkeypatch, gemini=Answers(("gemini-3.8-flash", one("Salut."))))
    done = pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
    assert done[0].text == "Salut." and swapped(found, done) == []


def test_a_job_part_translated_by_the_pick_still_names_the_other_once(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(t, "hello there") for t in (0.0, 400.0, 800.0)]
    engines(monkeypatch, gemini=Answers((PICKED, one("un")), ("gemini-3.8-flash", one("deux")),
                                        ("gemini-3.8-flash", one("trois"))))
    with config.using({"gemini_model": PICKED}):
        done = pipeline.translate(job(tmp_path), lines)
    [note] = swapped(found, done)
    assert note["picked"] == "Gemini 4 Hydrogen" and note["used"] == ["Gemini 3.8 Flash"]


def test_lines_the_backup_translated_name_the_backup(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    lines = [said(0.0, "Hello."), said(400.0, "Bye.")]
    chosen = Answers((PICKED, one("Bonjour.")), (PICKED, QuotaExhausted("quota used up")))
    backup = Answers(("qwen3:8b", one("Au revoir.")))
    engines(monkeypatch, gemini=chosen, local=backup)
    with config.using({"gemini_model": PICKED, "local_model": "qwen3:8b"}):
        done = pipeline.translate(job(tmp_path), lines)
    assert [c.text for c in done] == ["Bonjour.", "Au revoir."]
    [note] = swapped(found, done)
    assert note["picked"] == "Gemini 4 Hydrogen" and note["used"] == ["Qwen3:8b"]


def test_a_backup_that_wrote_nothing_is_not_named(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, found: Findings) -> None:
    chosen = Answers((PICKED, one("Bonjour.")))
    engines(monkeypatch, gemini=chosen, local=Answers())
    done = pipeline.translate(job(tmp_path), [said(0.0, "Hello.")])
    assert swapped(found, done) == []


def test_antigravity_says_its_low_variant_answered_for_the_picked_effort(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], _prompt: str, _folder: str) -> Any:
        if command[-1].endswith("-high"):
            return subprocess.CompletedProcess(command, 1, "", "503 overloaded")
        envelope = {"status": "SUCCESS", "structured_output": {"result": one("Bonjour.")}}
        return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

    antigravity.forget()
    monkeypatch.setattr(antigravity, "listing", lambda: "gemini-3.8-flash-high\tHigh\n"
                                                        "gemini-3.8-flash-low\tLow\n")
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    monkeypatch.setattr(antigravity, "run", fake_run)
    asker = antigravity.AntigravityAsker()
    with config.using({"antigravity_model": "gemini-3.8-flash-high"}):
        assert asker.ask("Translate.", None, {}) == one("Bonjour.")
    assert asker.model_used == "gemini-3.8-flash-low"
    antigravity.forget()


def test_codex_says_which_model_answered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subscription, "codex_models", lambda: ["gpt-6-codex", "gpt-5.5-codex"])
    monkeypatch.setattr(subscription, "save", lambda *_args: None)

    def once(_self: Any, _prompt: str, _schema: Any, model: str) -> Any:
        if model == "gpt-6-codex":
            return subprocess.CompletedProcess([], 1, "", subscription.REFUSED), ""
        return subprocess.CompletedProcess([], 0, "", ""), json.dumps({"result": one("Salut.")})

    monkeypatch.setattr(subscription.CodexAsker, "once", once)
    asker = subscription.CodexAsker()
    assert asker.ask("Translate.", None, {}) == one("Salut.")
    assert asker.model_used == "gpt-5.5-codex"
