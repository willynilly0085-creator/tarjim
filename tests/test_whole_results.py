"""A video is written beside its final name and moved there only once it is whole: a cancel or
a failed run never leaves a broken video behind, nor removes the good one an earlier run made."""
import subprocess
from pathlib import Path

import pytest

from tarjim.dub import mix
from tarjim.render import burn


class Stopped(BaseException):
    """Stands in for a cancel, which is not an ordinary error."""


def burning(monkeypatch: pytest.MonkeyPatch, outcome: str, written: list[Path]) -> None:
    def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        written.append(Path(command[-1]))
        Path(command[-1]).write_bytes(b"half a video")
        if outcome == "cancel":
            raise Stopped
        return subprocess.CompletedProcess(command, 0 if outcome == "works" else 1, "", "no")

    monkeypatch.setattr(burn, "run", run)
    monkeypatch.setattr(burn, "ceiling_kbps", lambda _video: 0)
    monkeypatch.setattr(burn, "sound_codecs", lambda _video: ["aac"])
    monkeypatch.setattr(burn, "tool", lambda _name: "ffmpeg")


@pytest.mark.parametrize("outcome", ["fails", "cancel"])
def test_a_failed_or_cancelled_burn_keeps_the_earlier_video(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    target = tmp_path / "clip.ar.mp4"
    target.write_bytes(b"the good video")
    written: list[Path] = []
    burning(monkeypatch, outcome, written)
    with pytest.raises((RuntimeError, Stopped)):
        burn.encode(tmp_path / "clip.mp4", target, tmp_path, None)
    assert target.read_bytes() == b"the good video"
    assert written and target not in written
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.ar.mp4"]


def test_a_burn_that_works_replaces_the_earlier_video(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "clip.ar.mp4"
    target.write_bytes(b"the good video")
    burning(monkeypatch, "works", [])
    assert burn.encode(tmp_path / "clip.mp4", target, tmp_path, None) == target
    assert target.read_bytes() == b"half a video"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.ar.mp4"]


def test_a_failed_dub_keeps_the_earlier_dub(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "clip.ar.dub.mp4"
    target.write_bytes(b"the good dub")

    def ffmpeg(args: list[str], _data: bytes | None = None) -> bytes:
        Path(args[-1]).write_bytes(b"half a dub")
        raise RuntimeError("ffmpeg stopped")

    monkeypatch.setattr(mix, "ffmpeg", ffmpeg)
    with pytest.raises(RuntimeError):
        mix.mux(tmp_path / "picture.mp4", tmp_path / "dub.wav", target)
    assert target.read_bytes() == b"the good dub"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["clip.ar.dub.mp4"]
