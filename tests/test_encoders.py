import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tarjim.phone import delivery
from tarjim.render import burn
from tarjim.render.encoders import for_quality, for_rate


def test_every_computer_has_an_encoder_left_after_the_cards_and_x264() -> None:
    names = [encoder[1] for encoder in for_quality(3000)]
    assert names == ["h264_nvenc", "h264_qsv", "h264_amf", "libx264", "libopenh264", "h264_mf"]
    assert [encoder[1] for encoder in for_rate(900)][-2:] == ["libopenh264", "h264_mf"]
    assert for_quality(0)[-1][-2:] == ["-b:v", "4000k"]


def fake_ffmpeg(works: str, tried: list[str]) -> Any:
    def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        encoder = command[command.index("-c:v") + 1]
        tried.append(encoder)
        if encoder == works:
            Path(command[-1]).write_bytes(b"video")
        return subprocess.CompletedProcess(command, 0 if encoder == works else 1, "", "no")
    return run


def test_a_burn_without_nvidia_or_x264_uses_openh264(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tried: list[str] = []
    monkeypatch.setattr(burn, "run", fake_ffmpeg("libopenh264", tried))
    monkeypatch.setattr(burn, "video_kbps", lambda _video: 2000)
    monkeypatch.setattr(burn, "codec", lambda _video: "h264")
    monkeypatch.setattr(burn, "sound_codecs", lambda _video: ["aac"])
    monkeypatch.setattr(burn, "tool", lambda _name: "ffmpeg")
    target = burn.encode(tmp_path / "in.mp4", tmp_path / "out.mp4", tmp_path, None)
    assert target.read_bytes() == b"video" and tried[-1] == "libopenh264"
    assert "libx264" in tried


FFMPEG = shutil.which("ffmpeg")


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg with VP9 and H.264 encoders")
@pytest.mark.parametrize("case", [
    ("libvpx-vp9", "vp9", 1840), ("libx264", "h264", 1150), ("mpeg4", "mpeg4", 1150)])
def test_the_burns_ceiling_gives_h264_the_bits_the_sources_codec_saved(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: tuple[str, str, int]) -> None:
    encoder, found, ceiling = case
    clip = tmp_path / "clip.mkv"
    subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=64x36:rate=10", "-t", "1", "-c:v", encoder, str(clip)],
                   check=True)
    monkeypatch.setattr(burn, "tool", lambda name: shutil.which(name) or name)
    monkeypatch.setattr(burn, "video_kbps", lambda _video: 1000)
    assert burn.codec(clip) == found and burn.ceiling_kbps(clip) == ceiling


def test_the_phone_copy_without_x264_uses_the_next_encoder(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import media

    tried: list[str] = []
    video = tmp_path / "big.mp4"
    video.write_bytes(b"x" * (delivery.DIRECT + 1))
    monkeypatch.setattr(media, "run", fake_ffmpeg("h264_mf", tried))
    monkeypatch.setattr(media, "tool", lambda _name: "ffmpeg")
    monkeypatch.setattr(media, "probe", lambda _v: type("P", (), {"duration": 60.0})())
    made = delivery.phone_copy(video)
    assert made is not None and made.read_bytes() == b"video" and tried[-1] == "h264_mf"
