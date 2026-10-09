"""Dubbing and listening say when they could not do the job, and nothing leaves the computer
that the person did not choose."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from tarjim import gemini_client, job, media
from tarjim.dub import fish, make
from tarjim.dub.lines import Line
from tarjim.engines import app_install
from tarjim.engines.catalog import BY_ID
from tarjim.listen import gemini_listen
from tarjim.server import connections
from tarjim.server.jobs import classify

LINES = [Line(0.0, 1.0, "S1", "مرحبا", "hi"), Line(1.0, 2.0, "S1", "وداعا", "bye")]


def test_a_voice_kept_on_the_computer_never_becomes_a_cloud_voice(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(make, "setting", lambda _name: "")
    assert make.choose("clone", "sw") == "clone"
    for engine in ("clone", "gemini", "fish"):
        with pytest.raises(make.DubUnavailable):
            make.choose(engine, "ur")


def test_a_failed_natural_voice_says_so_when_no_voice_is_installed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    class Limited:
        def speak_all(self, _lines: list[Line]) -> list[np.ndarray]:
            raise RuntimeError("Gemini voice: 10 requests a day used up")

    monkeypatch.setattr(make, "voices_for", lambda *_a: Limited())
    monkeypatch.setattr(make, "clone_installed", lambda: False)
    order: Any = SimpleNamespace(dub="gemini", target="ar")
    with pytest.raises(RuntimeError, match="used up"):
        make.speak("gemini", order, {}, LINES)


def test_a_dub_where_every_line_is_silent_is_a_failure() -> None:
    voices: Any = object.__new__(fish.FishVoices)
    voices.owned, voices.session = [], None
    voices.speak = lambda _line: np.zeros(0, dtype=np.float32)
    with pytest.raises(RuntimeError, match="no line"):
        voices.speak_all(LINES)


def test_a_rejected_key_stops_at_once_and_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    client: Any = object.__new__(gemini_client.GeminiClient)
    client.spent, client.cooling, calls = set(), {}, []

    def refuse(model: str, *_rest: Any) -> Any:
        calls.append(model)
        error = RuntimeError("API key not valid. Please pass a valid API key.")
        error.code = 400  # type: ignore[attr-defined]
        raise error

    monkeypatch.setattr(client, "call", refuse, raising=False)
    with pytest.raises(RuntimeError) as caught:
        client.ask("p", None, {})
    assert len(calls) == 1 and classify(caught.value) == "key"


def test_listening_that_returns_nothing_readable_is_a_failure() -> None:
    silent: Any = SimpleNamespace(ask=lambda *_a: None)
    with pytest.raises(RuntimeError):
        gemini_listen.listen(b"sound", silent)


def test_a_video_without_sound_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    done = SimpleNamespace(returncode=1, stderr="Output file does not contain any stream")
    monkeypatch.setattr(media, "run", lambda *_a, **_k: done)
    monkeypatch.setattr(media, "tool", lambda name: name)
    with pytest.raises(RuntimeError, match="sound"):
        media.extract_audio(tmp_path / "mute.mp4", tmp_path / "audio.wav")


def test_work_kept_for_one_video_is_not_used_for_another_with_the_same_name(
        tmp_path: Path) -> None:
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"first")
    first = job.Job(video)
    first.claim_cache()
    (first.cache / "transcript.json").write_text("{}", encoding="utf-8")
    first.claim_cache()
    assert (first.cache / "transcript.json").exists()
    video.write_bytes(b"a different recording")
    job.Job(video).claim_cache()
    assert not (first.cache / "transcript.json").exists()


def test_a_running_job_can_be_stopped_between_dubbing_steps() -> None:
    seen: list[str] = []
    token = job.CHECKPOINT.set(lambda: seen.append("asked"))
    job.checkpoint()
    job.CHECKPOINT.reset(token)
    job.checkpoint()
    assert seen == ["asked"]


def test_grok_can_be_installed_without_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_install, "npm", lambda: "")
    assert connections.subscription_view(BY_ID["grok"])["can_install"] is True
    assert connections.subscription_view(BY_ID["codex"])["can_install"] is False
