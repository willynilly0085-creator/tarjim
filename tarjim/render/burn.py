"""Burn the subtitles, and tarjim's mark (render/mark.py), into the picture in one pass. ffmpeg
reads the subtitle file's name inside a filter description, where quotes, colons and backslashes
have meanings of their own, so the file is written under a plain name and ffmpeg runs in that
folder. The mark's logo is a second input, opened as a PNG and nothing else.

The encoders aim at a quality, not a size, and on a clip that was already compressed hard (a
phone video, a download) that alone made the result two to three times larger than the source:
measured, 48 MB in and 127 MB out. Writing text onto a picture adds no detail worth those bits,
so the result may spend a little more than the source did and no more."""
import tempfile
from pathlib import Path

from tarjim.media import picture, run, source, tool, video_kbps
from tarjim.render.encoders import for_quality
from tarjim.render.mark import LOGO, Mark, overlay, with_mark

PLAIN = "subtitles.ass"
HEADROOM = 1.15


def burn(video: Path, subtitles: str, target: Path, mark: Mark | None = None) -> Path:
    """The video with these subtitles (an .ass text) and, unless it is None, the mark."""
    with tempfile.TemporaryDirectory(prefix="tarjim-burn-") as folder:
        (Path(folder) / PLAIN).write_text(with_mark(subtitles, mark), encoding="utf-8")
        return encode(video.resolve(), target.resolve(), Path(folder), mark)


def drawing(mark: Mark | None) -> list[str]:
    if mark is None:
        return ["-vf", f"ass={PLAIN}"]
    return [*picture(LOGO), "-filter_complex", f"[0:v]ass={PLAIN}[subtitled];"
            + overlay(mark, "subtitled")]


def ceiling(rate: int) -> list[str]:
    return ["-maxrate", f"{rate}k", "-bufsize", f"{2 * rate}k"] if rate else []


def encode(video: Path, target: Path, folder: Path, mark: Mark | None) -> Path:
    base = [tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", *source(video),
            *drawing(mark), "-c:a", "copy", "-movflags", "+faststart"]
    rate = int(video_kbps(video) * HEADROOM)
    errors, limit = [], ceiling(rate)
    for encoder in for_quality(rate):
        result = run([*base, *encoder, *limit, str(target)], cwd=folder)
        if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
            return target
        errors.append(result.stderr.strip()[-200:])
    target.unlink(missing_ok=True)
    raise RuntimeError("burn failed: " + " | ".join(errors))
