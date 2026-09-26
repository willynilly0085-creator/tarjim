import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SCENE_THRESHOLD = 0.25
MIN_CUT_SPACING = 0.2
SAMPLE_RATE = 16000
PTS = re.compile(r"pts_time:([\d.]+)")


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration: float


def tool(name: str) -> str:
    override = os.environ.get(f"TARJIM_{name.upper()}")
    found = override or shutil.which(name)
    if not found:
        raise FileNotFoundError(f"{name} not found; install it or set TARJIM_{name.upper()}")
    return found


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)


def probe(video: Path) -> VideoInfo:
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height:format=duration", "-of", "json",
               str(video)])
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    return VideoInfo(stream["width"], stream["height"], float(data["format"]["duration"]))


def extract_audio(video: Path, target: Path) -> Path:
    run([tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
         "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), str(target)])
    return target


def audio_bytes(video: Path) -> bytes:
    result = subprocess.run(
        [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", str(video), "-vn",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-b:a", "48k", "-f", "mp3", "-"],
        capture_output=True, check=False)
    return result.stdout


def scene_cuts(video: Path, threshold: float = SCENE_THRESHOLD) -> list[float]:
    out = run([tool("ffmpeg"), "-hide_banner", "-i", str(video), "-an",
               "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    times = sorted({round(float(t), 2) for t in PTS.findall(out.stderr)})
    return [t for i, t in enumerate(times) if i == 0 or t - times[i - 1] > MIN_CUT_SPACING]
