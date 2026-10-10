"""Burn the subtitles into the picture. ffmpeg reads the subtitle file's name inside a filter
description, where quotes, colons and backslashes have meanings of their own, so the file is
copied under a plain name and ffmpeg runs in that folder.

The encoders aim at a quality, not a size, and on a clip that was already compressed hard (a
phone video, a download) that alone made the result two to three times larger than the source:
measured, 48 MB in and 127 MB out. Writing text onto a picture adds no detail worth those bits,
so the result may spend a little more than the source did and no more."""
import shutil
import tempfile
from pathlib import Path

from tarjim.media import run, tool, video_kbps

ENCODERS = [
    ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"],
    ["-c:v", "libx264", "-crf", "19", "-preset", "medium"],
]
PLAIN = "subtitles.ass"
HEADROOM = 1.15


def burn(video: Path, ass: Path, target: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="tarjim-burn-") as folder:
        shutil.copyfile(ass, Path(folder) / PLAIN)
        return encode(video.resolve(), target.resolve(), Path(folder))


def ceiling(video: Path) -> list[str]:
    rate = int(video_kbps(video) * HEADROOM)
    return ["-maxrate", f"{rate}k", "-bufsize", f"{2 * rate}k"] if rate else []


def encode(video: Path, target: Path, folder: Path) -> Path:
    base = [tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
            "-vf", f"ass={PLAIN}", "-c:a", "copy", "-movflags", "+faststart"]
    errors, limit = [], ceiling(video)
    for encoder in ENCODERS:
        result = run([*base, *encoder, *limit, str(target)], cwd=folder)
        if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
            return target
        errors.append(result.stderr.strip()[-200:])
    target.unlink(missing_ok=True)
    raise RuntimeError("burn failed: " + " | ".join(errors))
