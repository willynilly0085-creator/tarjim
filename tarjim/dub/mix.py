from pathlib import Path

import numpy as np

from tarjim.dub.audio import RATE, ffmpeg, fit, speed_up, trim
from tarjim.dub.lines import Line

HEADROOM = 0.97
VOICE_GAIN = 1.0
MIN_ROOM = 0.3
GRACE = 0.25


def place(track: np.ndarray, line: Line, wav: np.ndarray) -> None:
    if wav.size == 0:
        return
    room = max(line.room, MIN_ROOM)
    voice = trim(wav)
    fitted = fit(speed_up(voice, (voice.size / RATE) / room), room + GRACE)
    start = int(line.start * RATE)
    end = min(start + fitted.size, track.shape[0])
    if end > start:
        track[start:end] += fitted[:end - start, None] * VOICE_GAIN


def mix(lines: list[Line], speech: list[np.ndarray], background: np.ndarray) -> np.ndarray:
    track = np.zeros_like(background)
    for line, wav in zip(lines, speech, strict=True):
        place(track, line, wav)
    track += background
    peak = float(np.max(np.abs(track))) if track.size else 0.0
    return track * (HEADROOM / peak) if peak > HEADROOM else track


def mux(picture: Path, sound: Path, target: Path) -> Path:
    ffmpeg(["-y", "-i", str(picture), "-i", str(sound), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-shortest", str(target)])
    return target
