"""When the chosen listener fails or hears nothing: the person sees the listener's own error when
nothing can stand in for it, a video with no speech finishes with no subtitles, a backup's or an
empty hearing is not kept for the next run, and the local listener is not run twice."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim import hearing, media
from tarjim.asr import align, qwen
from tarjim.asr.base import Transcript
from tarjim.engines import choice
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word

SAID = [Word("Hello", 0.2, 0.6), Word("there.", 0.7, 1.1)]


def not_installed(_audio: Path) -> Any:
    raise OSError("Qwen/Qwen3-ASR is not a local folder")


def quiet_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Job:
    """A job whose sound is a second of silence."""
    import tarjim.memory

    def extract(_video: Path, target: Path) -> Path:
        soundfile.write(target, np.zeros(16000, dtype=np.float32), 16000)
        return target

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(media, "extract_audio", extract)
    return Job(tmp_path / "v.mp4", cache_dir=tmp_path / "cache")


def answering(monkeypatch: pytest.MonkeyPatch, heard: Heard | Exception) -> None:
    def listen(_video: Path, _audio: Path) -> Heard:
        if isinstance(heard, Exception):
            raise heard
        return heard

    monkeypatch.setattr(hearing, "listen_video", listen)


def test_the_listener_error_is_shown_when_no_local_listener_can_stand_in(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, RuntimeError("gemini 400: API key not valid"))
    monkeypatch.setattr(hearing, "qwen_transcript", not_installed)
    with pytest.raises(RuntimeError, match="API key not valid"):
        hearing.transcript_for(job, lambda _stage: None)
    assert not (job.cache / "transcript.json").exists()


def test_a_video_with_no_speech_finishes_with_no_subtitles(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, Heard("", [], [[]]))
    monkeypatch.setattr(hearing, "qwen_transcript", not_installed)
    assert hearing.transcript_for(job, lambda _stage: None).words == []
    assert not (job.cache / "heard.json").exists()
    assert not (job.cache / "transcript.json").exists()


def test_a_backup_hearing_is_used_but_not_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = quiet_job(tmp_path, monkeypatch)
    answering(monkeypatch, RuntimeError("every listening pass failed"))
    monkeypatch.setattr(hearing, "qwen_transcript", lambda _a: Transcript("English", "Hi", SAID))
    assert hearing.transcript_for(job, lambda _stage: None).words == SAID
    assert not (job.cache / "transcript.json").exists()


class Engine:
    def __init__(self) -> None:
        self.runs = 0

    def transcribe(self, _path: str) -> Transcript:
        self.runs += 1
        return Transcript("English", "Hello there.", SAID)


class Aligner:
    def align(self, _wav: Any, utterances: list[Utterance], _language: str) -> list[Word]:
        return [w for u in utterances for w in align.proportional(u)]


def test_the_local_listener_is_its_own_second_opinion(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Engine()
    monkeypatch.setattr(qwen, "shared_engine", lambda: engine)
    monkeypatch.setattr(align, "shared_aligner", Aligner)
    monkeypatch.setattr(choice, "chain", lambda _task: ["local"])
    job = quiet_job(tmp_path, monkeypatch)
    words = hearing.transcript_for(job, lambda _stage: None).words
    assert [w.text for w in words] == ["Hello", "there."] and engine.runs == 1
    assert (job.cache / "transcript.json").exists()
