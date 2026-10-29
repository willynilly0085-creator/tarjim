"""A sound file without a picture asked to be dubbed gets a dubbed sound file, not nothing."""
from pathlib import Path

import pytest

from tarjim import media, pipeline
from tarjim.dub import make, mix
from tarjim.job import Job
from tarjim.models import Cue, Word

CUES = [Cue(0.0, 1.0, [Word("Hi", 0.0, 0.5)], text="هلا")]


def test_sound_alone_is_dubbed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pictures: list[Path | None] = []
    monkeypatch.setattr(pipeline.media, "probe", lambda _v: media.VideoInfo(0, 0, 9.0))
    monkeypatch.setattr(make, "dub_video", lambda _j, _c, _w, picture: pictures.append(picture))
    job = Job(tmp_path / "talk.mp3", dub="gemini", out_dir=tmp_path, cache_dir=tmp_path / "c")
    pipeline.write_outputs(job, CUES, [], pipeline.quiet)
    assert pictures == [None] and job.output(".srt").exists()


def test_a_dub_without_a_picture_is_written_as_sound_only(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[list[str]] = []

    def ffmpeg(args: list[str]) -> bytes:
        asked.append(args)
        Path(args[-1]).write_bytes(b"sound")  # the part file, moved into place when whole
        return b""

    monkeypatch.setattr(mix, "ffmpeg", ffmpeg)
    assert mix.mux(None, tmp_path / "dub.wav", tmp_path / "talk.ar.dub.mp4").is_file()
    assert "0:a:0" in asked[0] and "0:v:0" not in asked[0] and "-c:v" not in asked[0]
