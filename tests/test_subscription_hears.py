"""A Gemini subscription can listen: the sound is handed to its program as a file."""
from pathlib import Path
from typing import Any

import pytest

from tarjim.engines import antigravity, choice
from tarjim.engines.antigravity import HEAR, SOUND, AntigravityAsker
from tarjim.engines.web import EngineError
from tarjim.listen.gemini_listen import listen

SAID = {"start": 0.0, "end": 1.5, "speaker": "S1", "text": "Hello there."}
ANSWER = {"language": "English", "utterances": [SAID]}


@pytest.fixture
def program(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def once(_self: AntigravityAsker, *given: Any) -> Any:
        prompt, audio, _schema, model = given
        calls.append({"prompt": prompt, "audio": audio, "model": model})
        if len(calls) == 1 and audio == b"flaky":
            raise EngineError("antigravity", 1, "Eligibility check failed: UNAVAILABLE (code 503)")
        return ANSWER

    monkeypatch.setattr(AntigravityAsker, "once", once)
    monkeypatch.setattr(antigravity, "hearing_model", lambda: "gemini-flash-low")
    return calls


def test_the_sound_goes_as_a_file_to_the_lightest_model(program: list[dict[str, Any]]) -> None:
    language, utterances = listen(b"mp3", AntigravityAsker())
    assert (language, utterances[0].text) == ("English", "Hello there.")
    assert program[0]["prompt"].startswith(HEAR) and SOUND in HEAR
    assert program[0]["model"] == "gemini-flash-low"


def test_a_busy_service_is_asked_once_more(program: list[dict[str, Any]]) -> None:
    listen(b"flaky", AntigravityAsker())
    assert len(program) == 2


def test_the_file_is_written_beside_the_program(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, bytes] = {}

    def run(command: list[str], _prompt: str, folder: str) -> Any:
        seen["sound"] = (Path(folder) / SOUND).read_bytes()
        raise EngineError("antigravity", 0, "stop here")

    monkeypatch.setattr(antigravity, "run", run)
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    with pytest.raises(EngineError):
        AntigravityAsker().once("ask", b"the sound", {"type": "object"}, "")
    assert seen["sound"] == b"the sound"


def test_a_signed_in_subscription_counts_as_a_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(choice, "subscribed", lambda provider: provider == "antigravity")
    assert choice.usable("antigravity", "listen")
    assert not choice.usable("claude", "listen")


def test_passes_that_agree_on_the_words_are_not_voted_away() -> None:
    from tarjim.listen.gemini_listen import Utterance
    from tarjim.listen.merge import settled

    full = [Utterance(float(n), n + 0.9, "S1", f"line number {n} said here") for n in range(10)]
    drifted = [Utterance(u.start + 9.0, u.end + 9.0, u.speaker, u.text) for u in full]
    assert settled(full[:5], [full, drifted, full]) == full
    assert settled(full[:5], [full, full[:5], full[:4]]) == full[:5]
