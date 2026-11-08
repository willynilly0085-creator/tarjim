"""Which hearings are kept (2026-11-08): a backup engine's is used and never kept, so the chosen
engine is tried again on the next run; a cloud hearing with no speech is kept with a count, so it
is paid for at most TRIES times; and a local listener that cannot run, even out of memory, never
fails a clip the cloud heard no speech in."""
import dataclasses
from pathlib import Path
from typing import Any

import pytest
from test_hearing_fallback import SAID, Aligner, answering, not_installed, quiet_job

from tarjim import hearing
from tarjim.asr import align, vad
from tarjim.engines import choice
from tarjim.listen.asked import TRIES
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard

HELLO = [Utterance(0.2, 1.1, "S1", "Hello there.")]


def test_a_backup_engines_hearing_is_used_but_never_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def listen_with(provider: str, _video: Path, _audio: Path) -> Heard:
        calls.append(provider)
        if provider == "gemini":
            raise RuntimeError("gemini 503: the model is overloaded")
        return Heard("English", HELLO, [HELLO], SAID)

    monkeypatch.setattr(choice, "chain", lambda _task: ["gemini", "local"])
    monkeypatch.setattr(hearing, "listen_with", listen_with)
    monkeypatch.setattr(align, "shared_aligner", Aligner)
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [])  # no model is loaded
    job = quiet_job(tmp_path, monkeypatch)
    for _run in range(2):
        words = hearing.transcript_for(job, lambda _stage: None).words
        assert [w.text for w in words] == ["Hello", "there."]
    assert calls == ["gemini", "local", "gemini", "local"]
    # the speech map is the sound's, whichever engine heard it (listen/clipmap.py, 2026-11-09)
    kept = [p.name for p in job.cache.iterdir() if p.suffix == ".json"]
    assert kept in ([], ["speech.json"])


def raising(error: Exception) -> Any:
    def transcribe(_audio: Path) -> Any:
        raise error

    return transcribe


WEAK = [RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB"), MemoryError(),
        ValueError("the model's weights could not be read")]


@pytest.mark.parametrize("error", WEAK, ids=lambda e: type(e).__name__)
def test_no_speech_and_a_local_listener_that_cannot_run_give_no_subtitles(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception,
        capsys: pytest.CaptureFixture[str]) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, Heard("", [], [[]], provider="gemini"))
    monkeypatch.setattr(hearing, "qwen_transcript", raising(error))
    assert hearing.transcript_for(job, lambda _stage: None).words == []
    assert "the listener on this computer could not stand in" in capsys.readouterr().out


@pytest.mark.parametrize("error", WEAK, ids=lambda e: type(e).__name__)
def test_the_listener_error_is_shown_when_the_local_one_cannot_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, RuntimeError("gemini 400: API key not valid"))
    monkeypatch.setattr(hearing, "qwen_transcript", raising(error))
    with pytest.raises(RuntimeError, match="API key not valid"):
        hearing.transcript_for(job, lambda _stage: None)


def test_a_cloud_hearing_with_no_speech_is_paid_for_at_most_twice(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    listened: list[int] = []

    def listen(_video: Path, _audio: Path) -> Heard:
        listened.append(1)
        return Heard("English", [], [[], [], []], provider="gemini")

    monkeypatch.setattr(hearing, "listen_video", listen)
    monkeypatch.setattr(hearing, "qwen_transcript", not_installed)
    for _run in range(4):
        assert hearing.transcript_for(job, lambda _stage: None).words == []
    assert len(listened) == TRIES
    hearing.transcript_for(dataclasses.replace(job, relisten=True), lambda _stage: None)
    assert len(listened) == TRIES + 1  # "listen again" starts the count afresh


def test_a_backup_that_heard_no_speech_is_not_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, Heard("English", [], [[]], provider="openai", backup=True))
    monkeypatch.setattr(hearing, "qwen_transcript", not_installed)
    assert hearing.transcript_for(job, lambda _stage: None).words == []
    assert not (job.cache / "heard.json").exists()
