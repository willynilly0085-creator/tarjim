"""What text the picture shows, and when, over the whole video: every key frame, read small and
grey in one ffmpeg run, each turned at once into the text bands it carries (render/text_bands.py)
and dropped, so an hour costs a few hundred numbers, not a few hundred pictures.

Only key frames are decoded. A bitstream filter drops the other packets before the decoder
because VP9's decoder ignores -skip_frame and decoded every frame: a 2-minute 1080p VP9 clip
took 5.6 s that way and 0.3 s with the filter. At most one frame a second is kept, for files in
which every frame is a key frame. Key frames are 1 to 10 seconds apart on the videos people
bring (3 s on the clip this was made for), so this says roughly when text shows; the moments
that decide a line are then read exactly (render/moments.py).

Measured on one core: a 4-minute 1080p H.264 clip in 0.6 s, an hour of it in 7.6 s, two minutes
of 1080p AV1 in 0.2 s. The budget is a hundredth of the video, between 5 and 30 seconds; a slow
computer that runs out has looked at the first part of the video, and the rest keeps the video's
one place."""
import re
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO

import numpy as np

from tarjim.media import source, tool
from tarjim.render.text_bands import Band, frame_bands

WIDTH = 480
SHARE = 0.01
SHORTEST, LONGEST = 5.0, 30.0
GRACE = 1.0
KEYS_ONLY = ["-bsf:v", "noise=drop=not(key)"]
ONE_A_SECOND = "select=isnan(prev_selected_t)+gte(t-prev_selected_t\\,1)"
TIME = re.compile(rb"pts_time:\s*(-?[0-9.]+)")
# Each frame's moment, in seconds from the start, and the text bands it shows.
Seen = dict[float, list[Band]]


def budget(length: float) -> float:
    return min(LONGEST, max(SHORTEST, length * SHARE))


def rows_for(shape: tuple[int, int]) -> int:
    """The frame's height at WIDTH, even, so every frame is the same number of bytes."""
    width, height = shape
    return max(2, 2 * round(WIDTH * height / width / 2))


def command(video: Path, rows: int, keys_only: bool) -> list[str]:
    return [tool("ffmpeg"), "-hide_banner", "-nostats", "-loglevel", "info", "-threads", "1",
            *(KEYS_ONLY if keys_only else []), "-skip_frame", "nokey", *source(video),
            "-an", "-sn", "-dn", "-fps_mode", "passthrough",
            "-vf", f"{ONE_A_SECOND},scale={WIDTH}:{rows}:flags=area,format=gray,showinfo",
            "-f", "rawvideo", "-"]


def scan(video: Path, shape: tuple[int, int], length: float) -> Seen:
    """The text bands of each key frame, by its moment, for as much as the budget allows."""
    deadline, rows = time.monotonic() + budget(length), rows_for(shape)
    for keys_only in (True, False):  # an ffmpeg before 7.0 has no bitstream filter on input
        seen = read(command(video, rows, keys_only), rows, deadline)
        if seen:
            return seen
    return {}


def frames_in(stream: IO[bytes], rows: int) -> Iterator[np.ndarray]:
    size = WIDTH * rows
    while len(chunk := stream.read(size)) == size:
        yield np.frombuffer(chunk, np.uint8).reshape(rows, WIDTH)


def times_in(stream: IO[bytes], into: list[float]) -> None:
    """showinfo prints each frame's moment as the frame leaves the filters, in order."""
    for line in stream:
        found = TIME.search(line)
        if found and b"showinfo" in line:
            into.append(float(found.group(1)))


def read(args: list[str], rows: int, deadline: float) -> Seen:
    left = deadline - time.monotonic()
    if left <= 0:
        return {}
    child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    out, err = child.stdout, child.stderr
    assert out is not None and err is not None
    times: list[float] = []
    listener = threading.Thread(target=times_in, args=(err, times), daemon=True)
    stop = threading.Timer(left, child.kill)
    listener.start()
    stop.start()
    try:
        bands = [frame_bands(frame) for frame in frames_in(out, rows)]
    finally:
        stop.cancel()
        child.kill()
        child.wait()
        listener.join(GRACE)
    return {round(at, 3): found for at, found in zip(times, bands, strict=False)}
