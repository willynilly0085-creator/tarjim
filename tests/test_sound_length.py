"""How long a file is comes from the sound ffmpeg decoded, never from what the file says about
itself, and no file decodes to more than tarjim's longest: a tiny file must not fill the disk or
the memory, and a lying header must not plan endless work that cancel cannot stop."""
import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import pytest

import tarjim.memory
from tarjim import hearing, media
from tarjim.dub import audio as dub_audio
from tarjim.dub import make
from tarjim.job import CHECKPOINT, Job
from tarjim.listen.chunks import listen_in_chunks
from tarjim.listen.merge import Heard
from tarjim.server.jobs import classify
from tarjim.ui_languages import FOLDER, codes

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
real_tools = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                reason="needs ffmpeg and ffprobe")
WAV_BYTES_PER_SECOND = media.SAMPLE_RATE * 2


class WentOn(Exception):
    pass


def silence(folder: Path, seconds: float, name: str = "quiet.mkv") -> Path:
    """Lossless silence: a few hundred bytes that decode to any length."""
    clip = folder / name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=8000:cl=mono", "-t", str(seconds), "-c:a", "flac",
                    str(clip)], check=True)
    return clip


def wav_of(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(media.SAMPLE_RATE)
        out.writeframes(b"\0\0" * int(seconds * media.SAMPLE_RATE))
    return path


def claims(monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    """The container's header states this length, whatever its sound holds."""
    stated = media.VideoInfo(64, 64, seconds)
    monkeypatch.setattr(media, "probe", lambda _video: stated)
    monkeypatch.setattr(make, "probe", lambda _video: stated, raising=False)


@real_tools
def test_ffmpeg_stops_writing_just_past_the_longest_sound(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "LONGEST", 3.0, raising=False)
    target, written = tmp_path / "audio.wav", []
    real_run = media.run

    def measured(args: list[str], cwd: Path | None = None) -> Any:
        done = real_run(args, cwd)
        written.append(target.stat().st_size if target.exists() else 0)
        return done

    monkeypatch.setattr(media, "run", measured)
    with pytest.raises(RuntimeError):
        media.extract_audio(silence(tmp_path, 20), target)
    assert written and max(written) <= 5 * WAV_BYTES_PER_SECOND


@real_tools
def test_sound_longer_than_the_longest_is_refused_by_name_and_leaves_nothing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "LONGEST", 3.0, raising=False)
    target = tmp_path / "audio.wav"
    with pytest.raises(RuntimeError, match="longer than six hours") as refused:
        media.extract_audio(silence(tmp_path, 20), target)
    assert classify(refused.value) == "long" and not target.exists()


@real_tools
def test_ordinary_sound_is_extracted_whole(tmp_path: Path) -> None:
    wav = media.extract_audio(silence(tmp_path, 2), tmp_path / "audio.wav")
    with wave.open(str(wav)) as sound:
        assert abs(sound.getnframes() / sound.getframerate() - 2.0) < 0.05


@real_tools
def test_a_failed_hearing_does_not_leave_the_sound_behind(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def nothing_heard(_audio: Path) -> None:
        raise RuntimeError("no speech was heard")

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(hearing, "listen_and_align", lambda *_a: None)
    monkeypatch.setattr(hearing, "local_transcript", nothing_heard)
    job = Job(silence(tmp_path, 2))
    with pytest.raises(RuntimeError):
        hearing.transcript_for(job, lambda _stage: None)
    assert not (job.cache / "audio.wav").exists()


def test_cloud_listening_plans_from_the_sound_not_the_header(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claims(monkeypatch, 3.0e6)
    asked: list[bytes] = []
    monkeypatch.setattr(media, "audio_bytes", lambda *_a: b"sound")
    monkeypatch.setattr(hearing, "speech_regions_of", lambda _audio: [])
    monkeypatch.setattr(hearing, "cloud_listener", lambda _provider: lambda sound: (
        asked.append(sound), Heard("en", [], [[]]))[1])
    hearing.listen_with("gemini", tmp_path / "clip.mkv", wav_of(tmp_path / "audio.wav", 2.0))
    assert len(asked) == 1


def test_each_chunk_waits_for_the_pause_and_cancel_buttons() -> None:
    asked: list[float] = []

    def cancel_after_the_first() -> None:
        if asked:
            raise WentOn

    token = CHECKPOINT.set(cancel_after_the_first)
    try:
        with pytest.raises(WentOn):
            listen_in_chunks(1000.0, [], lambda start, _end: (
                asked.append(start), Heard("en", [], [[]]))[1])
    finally:
        CHECKPOINT.reset(token)
    assert asked == [0.0]


def dub_job(monkeypatch: pytest.MonkeyPatch, video: Path) -> Job:
    def went_on(*_a: object) -> None:
        raise WentOn

    monkeypatch.setattr(make, "choose", lambda *_a: "clone")
    monkeypatch.setattr(make, "spoken", went_on)
    return Job(video, dub="clone")


@real_tools
def test_dubbing_measures_the_sound_when_the_header_says_less(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claims(monkeypatch, 2.0)
    monkeypatch.setattr(media, "LONGEST", 5.0, raising=False)
    monkeypatch.setattr(make, "LONGEST", 5.0, raising=False)
    job = dub_job(monkeypatch, silence(tmp_path, 20))
    with pytest.raises(RuntimeError, match="longer than six hours"):
        make.dub_video(job, [], [], job.video)


@real_tools
def test_dubbing_goes_on_when_the_header_claims_more_than_the_sound(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claims(monkeypatch, 7 * 3600.0)
    job = dub_job(monkeypatch, silence(tmp_path, 2))
    with pytest.raises(WentOn):
        make.dub_video(job, [], [], job.video)


@real_tools
def test_the_dubbing_decode_stops_just_past_the_longest_sound(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "LONGEST", 3.0, raising=False)
    mixture = dub_audio.decode(silence(tmp_path, 20), channels=2)
    assert 3 * dub_audio.RATE <= len(mixture) <= 5 * dub_audio.RATE


def test_the_reason_is_shown_in_every_language() -> None:
    for code in codes():
        page = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        extension = json.loads((ROOT / "extension" / "_locales" / code / "messages.json")
                               .read_text(encoding="utf-8"))
        assert page.get("err_long") and extension.get("errLong", {}).get("message"), code
    assert '"long"' in (ROOT / "web" / "jobs.js").read_text(encoding="utf-8")
    assert 'long: "errLong"' in (ROOT / "extension" / "shared.js").read_text(encoding="utf-8")
