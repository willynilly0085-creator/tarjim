import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tarjim.config import setting

SCENE_THRESHOLD = 0.25
MIN_CUT_SPACING = 0.2
SAMPLE_RATE = 16000
PTS = re.compile(r"pts_time:([\d.]+)")
RUN_SECONDS = 6 * 3600


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration: float

    @property
    def has_picture(self) -> bool:
        return self.width > 0 and self.height > 0


def tool(name: str) -> str:
    found = setting(name) or shutil.which(name)
    if not found:
        raise FileNotFoundError(f"{name} not found; install it or set TARJIM_{name.upper()}")
    return found


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False, cwd=cwd, timeout=RUN_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{Path(args[0]).stem} did not finish within six hours") from None


def probe(video: Path) -> VideoInfo:
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:stream_disposition=attached_pic:format=duration",
               "-of", "json", str(video)])
    data = json.loads(out.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    cover = bool(stream.get("disposition", {}).get("attached_pic"))
    duration = float(data.get("format", {}).get("duration", 0.0))
    if cover:
        return VideoInfo(0, 0, duration)
    return VideoInfo(int(stream.get("width", 0)), int(stream.get("height", 0)), duration)


def video_kbps(video: Path) -> int:
    """How many kilobits a second the picture takes in this file; 0 when the file does not say."""
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=bit_rate:format=bit_rate", "-of", "json", str(video)])
    data = json.loads(out.stdout or "{}")
    stated = [(data.get("streams") or [{}])[0].get("bit_rate"), data.get("format", {}).get(
        "bit_rate")]
    return next((int(rate) // 1000 for rate in stated if str(rate or "").isdigit()), 0)


def extract_audio(video: Path, target: Path) -> Path:
    done = run([tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
                "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), str(target)])
    if done.returncode != 0 or not target.is_file():
        raise RuntimeError(f"this file has no sound that can be read: {done.stderr.strip()[-160:]}")
    return target


def audio_bytes(video: Path, start: float = 0.0, end: float | None = None) -> bytes:
    window = ["-ss", f"{start:.3f}"] + (["-to", f"{end:.3f}"] if end is not None else [])
    result = subprocess.run(
        [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", *window, "-i", str(video), "-vn",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-b:a", "48k", "-f", "mp3", "-"],
        capture_output=True, check=False)
    return result.stdout


def scene_cuts(video: Path, threshold: float = SCENE_THRESHOLD) -> list[float] | None:
    """Where the picture cuts; None when the scan itself failed, so the miss is not kept."""
    out = run([tool("ffmpeg"), "-hide_banner", "-i", str(video), "-an",
               "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    if out.returncode != 0:
        return None
    times = sorted({round(float(t), 2) for t in PTS.findall(out.stderr)})
    return [t for i, t in enumerate(times) if i == 0 or t - times[i - 1] > MIN_CUT_SPACING]


BRIGHT = 150.0
YAVG = re.compile(r"lavfi\.signalstats\.YAVG=(\d+(?:\.\d+)?)")
BOTTOM_STRIP = ("fps=1/4,crop=iw:ih/4:0:ih*3/4,scale=160:-1,signalstats,"
                "metadata=print:key=lavfi.signalstats.YAVG")


def mean_brightness(report: str) -> float:
    values = [float(v) for v in YAVG.findall(report)]
    return sum(values) / len(values) if values else 0.0


def bright_bottom(video: Path) -> bool:
    done = run([tool("ffmpeg"), "-hide_banner", "-i", str(video), "-vf", BOTTOM_STRIP, "-an",
                "-f", "null", "-"])
    return mean_brightness(done.stderr) > BRIGHT
