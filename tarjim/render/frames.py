"""A few small grey frames of the picture, taken while someone speaks, to see where the video
already carries text of its own.

Each frame is the key frame at or just before the moment asked for: ffmpeg seeks to it and
decodes nothing else, so a frame costs the same on a six-hour film as on a short clip. The decoder
gets one thread (four of them run at once): left to choose, it starts one per core in each of the
four and a weak computer spends its time switching between them. Measured on one core: 16 frames
of a 29-minute 1080p AV1 video in 6.7 s with that, 25 s without. Whatever is not read within
BUDGET seconds is left out; the moments are taken in an order that keeps any part of them spread
over the whole video."""
import subprocess
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from tarjim.media import source, tool
from tarjim.models import Cue

WIDTH = 480
MOST = 16
FEWEST_SPOKEN = 6
AT_ONCE = 4
BUDGET = 5.0
GRACE = 1.0
# The key frame at or just before the moment, and nothing else decoded.
QUICK = ["-skip_frame", "nokey", "-noaccurate_seek"]
Frame = np.ndarray


def sample_times(cues: list[Cue], duration: float) -> list[float]:
    """The middle of spoken lines, spread over the whole video; evenly spread without speech."""
    spoken = [(c.start + c.end) / 2 for c in cues if c.text.strip()]
    if len(spoken) < FEWEST_SPOKEN:
        return [duration * (i + 0.5) / MOST for i in range(MOST)]
    step = max(1.0, len(spoken) / MOST)
    return [spoken[int(i * step)] for i in range(min(MOST, len(spoken)))]


def spread(times: list[float]) -> list[float]:
    """Every fourth moment first, then the ones between: any first part covers the whole video."""
    return [times[i] for first in (0, 2, 1, 3) for i in range(first, len(times), 4)]


def command(video: Path, at: float, seek: list[str]) -> list[str]:
    return [tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-threads", "1", *seek,
            "-ss", f"{at:.2f}", *source(video), "-an", "-frames:v", "1",
            "-vf", f"scale={WIDTH}:-2:flags=area,format=gray", "-f", "rawvideo", "-"]


def frame_from(args: list[str], limit: float) -> Frame | None:
    try:
        done = subprocess.run(args, capture_output=True, check=False, timeout=limit)
    except subprocess.TimeoutExpired:
        return None
    raw = done.stdout
    if done.returncode != 0 or not raw or len(raw) % WIDTH:
        return None
    return np.frombuffer(raw, np.uint8).reshape(-1, WIDTH)


def grab(video: Path, at: float, limit: float = BUDGET) -> Frame | None:
    return frame_from(command(video, at, QUICK), limit)


def exact(video: Path, at: float, limit: float = BUDGET) -> Frame | None:
    """The frame shown at that very moment: ffmpeg decodes from the key frame before it, so it
    costs up to one key frame's spacing of decoding (render/moments.py takes few of them)."""
    return frame_from(command(video, at, []), limit)


def within_budget(times: list[float], take: Callable[[float, float], Frame | None]
                  ) -> list[Frame | None]:
    """take(moment, seconds left) for each moment, AT_ONCE at a time, for BUDGET seconds."""
    deadline = time.monotonic() + BUDGET

    def within(at: float) -> Frame | None:
        left = deadline - time.monotonic()
        return take(at, left + GRACE) if left > 0 else None

    with ThreadPoolExecutor(AT_ONCE) as pool:
        return list(pool.map(within, times))


def sample(video: Path, times: list[float]) -> list[Frame]:
    """The frames that could be read within BUDGET seconds, each once: two moments in one long
    shot give one frame."""
    grabbed = within_budget(spread(times), lambda at, limit: grab(video, at, limit))
    return list({f.tobytes(): f for f in grabbed if f is not None}.values())
