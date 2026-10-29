import json
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tarjim.config import setting

SCENE_THRESHOLD = 0.25
MIN_CUT_SPACING = 0.2
SAMPLE_RATE = 16000
PTS = re.compile(r"pts_time:([\d.]+)")
RUN_SECONDS = 6 * 3600
# Containers that hold their own picture and sound. A playlist or manifest (HLS, DASH, concat and
# the like) opens the files it names instead, so a stranger's "video" could make ffmpeg read any
# media file on this computer or a network share; ffmpeg refuses every other format before it
# reads anything past the file's first bytes.
CONTAINERS = "mov,matroska,avi,mp3,wav,flac,ogg,aac,mpegts,mpeg,flv,asf"
OWN_FILE_ONLY = ["-protocol_whitelist", "file", "-format_whitelist", CONTAINERS]
# tarjim's own pictures (the mark's logo) are PNG files and open as nothing else.
OWN_PICTURE = ["-protocol_whitelist", "file", "-format_whitelist", "png_pipe"]
NOT_MEDIA = "not a video or sound file tarjim can open"
# The most sound tarjim works on. A file of a few hundred bytes can decode to days of sound, so
# the length is measured on what ffmpeg decoded, never taken from what the file says about itself.
LONGEST = 6 * 3600.0
TOO_LONG = "this file is longer than six hours of sound, the most tarjim works on"
COUNT_RATE = 100
QUARTER = 90
# Sound laid on the file's own clock: silence where it starts late or skips, so the sound keeps
# its place against the picture instead of every line arriving early.
ON_THE_CLOCK = ["-af", "aresample=async=1:first_pts=0"]


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


def source(video: Path) -> list[str]:
    """How ffmpeg and ffprobe are handed a file that may come from a stranger."""
    return [*OWN_FILE_ONLY, "-i", str(video)]


def picture(image: Path) -> list[str]:
    """How ffmpeg is handed one of tarjim's own pictures."""
    return [*OWN_PICTURE, "-i", str(image)]


def check_readable(video: Path) -> None:
    """Before any work: the file is a video or sound file itself, not a list of other files."""
    done = run([tool("ffprobe"), "-v", "error", "-show_entries", "format=format_name",
                "-of", "csv=p=0", *source(video)])
    if done.returncode != 0 or not done.stdout.strip():
        raise RuntimeError(f"{NOT_MEDIA}: {done.stderr.strip()[-160:]}")


def on_its_side(stream: dict[str, Any]) -> bool:
    """A phone stores a standing clip lying down with a quarter turn to show it by; ffmpeg turns
    the picture when it decodes, so the size is the turned one. Older files keep the turn in a
    rotate tag."""
    turns = [d.get("rotation") for d in stream.get("side_data_list", [])]
    turns.append(stream.get("tags", {}).get("rotate"))
    return any(str(t).lstrip("-").isdigit() and int(t) % 180 == QUARTER for t in turns)


def probe(video: Path) -> VideoInfo:
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:stream_tags=rotate:stream_side_data=rotation:"
               "stream_disposition=attached_pic:format=duration", "-of", "json", *source(video)])
    data = json.loads(out.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    duration = float(data.get("format", {}).get("duration", 0.0))
    if stream.get("disposition", {}).get("attached_pic"):
        return VideoInfo(0, 0, duration)
    size = (int(stream.get("width", 0)), int(stream.get("height", 0)))
    width, height = size[::-1] if on_its_side(stream) else size
    return VideoInfo(width, height, duration)


def video_kbps(video: Path) -> int:
    """How many kilobits a second the picture takes in this file; 0 when the file does not say."""
    out = run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=bit_rate:format=bit_rate", "-of", "json", *source(video)])
    data = json.loads(out.stdout or "{}")
    stated = [(data.get("streams") or [{}])[0].get("bit_rate"), data.get("format", {}).get(
        "bit_rate")]
    return next((int(rate) // 1000 for rate in stated if str(rate or "").isdigit()), 0)


def sound_cap() -> list[str]:
    """ffmpeg stops a second past LONGEST, so a longer file is seen as longer and refused."""
    return ["-t", f"{LONGEST + 1:g}"]


def extract_audio(video: Path, target: Path) -> Path:
    """The sound as a wav that is later read whole into memory: never more than just past LONGEST,
    on disk (-fs as well, in case the file's timestamps confuse -t) or in memory."""
    most = int((LONGEST + 2) * SAMPLE_RATE * 2)
    done = run([tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", *source(video),
                "-vn", *ON_THE_CLOCK, "-ac", "1", "-ar", str(SAMPLE_RATE), *sound_cap(), "-fs",
                str(most), str(target)])
    if done.returncode != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        raise RuntimeError(f"this file has no sound that can be read: {done.stderr.strip()[-160:]}")
    if wav_seconds(target) > LONGEST:
        target.unlink()
        raise RuntimeError(TOO_LONG)
    return target


def wav_seconds(wav: Path) -> float:
    """How much sound ffmpeg really extracted."""
    try:
        with wave.open(str(wav), "rb") as sound:
            return sound.getnframes() / sound.getframerate()
    except (wave.Error, EOFError) as error:
        raise RuntimeError(f"this file has no sound that can be read: {error}") from None


def sound_seconds(video: Path) -> float:
    """How much sound the file really holds, decoded and counted (up to just past LONGEST)."""
    try:
        done = subprocess.run(
            [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", *source(video), "-vn",
             *ON_THE_CLOCK, "-ac", "1", "-ar", str(COUNT_RATE), *sound_cap(), "-f", "u8", "-"],
            capture_output=True, check=False, timeout=RUN_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg did not finish within six hours") from None
    return len(done.stdout) / COUNT_RATE


def audio_bytes(video: Path, start: float = 0.0, end: float | None = None) -> bytes:
    window = ["-ss", f"{start:.3f}"] + (["-to", f"{end:.3f}"] if end is not None else [])
    result = subprocess.run(
        [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", *window, *source(video), "-vn",
         *ON_THE_CLOCK, "-ac", "1", "-ar", str(SAMPLE_RATE), "-b:a", "48k", "-f", "mp3", "-"],
        capture_output=True, check=False)
    return result.stdout


def scene_cuts(video: Path, threshold: float = SCENE_THRESHOLD) -> list[float] | None:
    """Where the picture cuts; None when the scan itself failed, so the miss is not kept."""
    out = run([tool("ffmpeg"), "-hide_banner", *source(video), "-an",
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
    done = run([tool("ffmpeg"), "-hide_banner", *source(video), "-vf", BOTTOM_STRIP, "-an",
                "-f", "null", "-"])
    return mean_brightness(done.stderr) > BRIGHT
