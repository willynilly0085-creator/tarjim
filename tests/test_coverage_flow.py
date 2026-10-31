"""Speech a listening engine left out is found and filled, for any engine: a made-up cloud engine
here drops the end, drops the middle, drifts late, fails when asked again, and is checked with and
without the words this computer heard. A hearing that still misses speech is never kept."""
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim import hearing, media
from tarjim.asr import align, qwen, vad
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word

LENGTH = 250.0
RATE = 8000
SPOKEN = [Utterance(6.0 * k, 6.0 * k + 5.0, "S1", " ".join(f"w{k}x{i}" for i in range(10)))
          for k in range(40)]  # speech to 240 s
LOCAL = [w for u in SPOKEN for w in align.proportional(u)]
REGIONS = [(u.start, u.end) for u in SPOKEN]


class Aligner:
    def align(self, _wav: Any, utterances: list[Utterance], _language: str) -> list[Word]:
        return [w for u in utterances for w in align.proportional(u)]


class Engine:
    """A listening engine of no particular make: what it hears first, and how it hears again."""

    def __init__(self, first: list[Utterance], again_fails: bool = False) -> None:
        self.first, self.again_fails, self.asked = first, again_fails, 0

    def listen_video(self, _video: Path, _audio: Path) -> Heard:
        return Heard("English", self.first, [self.first], provider="fakecloud")

    def cloud_listener(self, provider: str) -> Any:
        assert provider == "fakecloud"
        return self.hear_slice

    def hear_slice(self, sound: bytes) -> Heard:
        self.asked += 1
        if self.again_fails:
            raise RuntimeError("fakecloud 500: busy")
        start, end = map(float, sound.decode().split(","))
        lines = [Utterance(u.start - start, u.end - start, u.speaker, u.text) for u in SPOKEN
                 if u.start >= start and u.end <= end]
        return Heard("English", lines, [lines])


def setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: Engine,
          local: list[Word] | None = LOCAL) -> Job:
    import tarjim.memory

    def extract(_video: Path, target: Path) -> Path:
        soundfile.write(target, np.zeros(int(LENGTH * RATE), dtype=np.float32), RATE)
        return target

    def heard_locally(_audio: Path) -> Transcript:
        if local is None:
            raise OSError("no local listener on this computer")
        return Transcript("English", "", local)

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(media, "extract_audio", extract)
    monkeypatch.setattr(media, "audio_bytes", lambda _v, s, e: f"{s},{e}".encode())
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: REGIONS)
    monkeypatch.setattr(hearing, "qwen_transcript", heard_locally)
    monkeypatch.setattr(hearing, "listen_video", engine.listen_video)
    monkeypatch.setattr(hearing, "cloud_listener", engine.cloud_listener)
    monkeypatch.setattr(align, "shared_aligner", Aligner)
    monkeypatch.setattr(qwen, "shared_engine", lambda: pytest.fail("not asked"))
    return Job(tmp_path / "clip.mp4", cache_dir=tmp_path / "cache")


def said(transcript: Transcript) -> set[str]:
    return {w.text for w in transcript.words}


def everything() -> set[str]:
    return {w.text for w in LOCAL}


def test_a_dropped_end_is_heard_again_by_the_same_engine(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    log = capsys.readouterr().out
    assert said(transcript) == everything() and engine.asked == 1
    assert "coverage: gap 162.0-239.0 s" in log and "re-listened with fakecloud: 13 lines" in log
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert len(kept["added"]) == 13 and (job.cache / "transcript.json").exists()


def test_a_kept_repair_is_used_again_without_asking(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine)
    hearing.transcript_for(job, lambda _stage: None)
    (job.cache / "transcript.json").unlink()
    assert said(hearing.transcript_for(job, lambda _stage: None)) == everything()
    assert engine.asked == 1


def test_late_times_are_not_taken_for_missing_speech_and_the_true_gap_is_found(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    stretched = [Utterance(u.start * 1.4, u.end * 1.4, u.speaker, u.text)
                 for u in SPOKEN if u.start < 178.0]  # stopped at 178 s, stretched to 250
    engine = Engine(stretched)
    job = setup(monkeypatch, tmp_path, engine)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    gaps = [line for line in capsys.readouterr().out.splitlines() if "coverage: gap" in line]
    assert said(transcript) == everything()
    start = float(gaps[0].split()[2].split("-")[0])
    assert len(gaps) == 1 and 179.0 <= start <= 182.0  # where it was said, not 250 s


def test_a_dropped_middle_is_filled(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if not 90.0 <= u.start < 130.0])
    job = setup(monkeypatch, tmp_path, engine)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    assert said(transcript) == everything()
    assert "coverage: gap 90.0-131.0 s" in capsys.readouterr().out


def test_an_engine_that_fails_again_leaves_the_local_words(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0], again_fails=True)
    job = setup(monkeypatch, tmp_path, engine)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    log = capsys.readouterr().out
    assert said(transcript) == everything()
    assert "listening again with fakecloud failed: fakecloud 500" in log
    assert "filled from local words: 130 words" in log
    assert (job.cache / "heard.json").exists()


def test_without_local_words_the_voice_detector_finds_the_gap(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine, local=None)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    assert said(transcript) == everything()
    assert "(65.0 s of speech, no words) -> re-listened with fakecloud" in capsys.readouterr().out


def test_speech_nothing_could_fill_is_logged_and_not_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0], again_fails=True)
    job = setup(monkeypatch, tmp_path, engine, local=None)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    log = capsys.readouterr().out
    assert "-> not repaired" in log and "this hearing is not kept" in log
    assert max(w.end for w in transcript.words) < 162.0
    assert not (job.cache / "heard.json").exists()
    assert not (job.cache / "transcript.json").exists()
