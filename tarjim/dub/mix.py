from pathlib import Path

import numpy as np

from tarjim.dub.audio import RATE, USUAL_PACE, Pace, ffmpeg, fit, speed_up, trim
from tarjim.dub.lines import Line
from tarjim.dub.loud import level
from tarjim.media import source
from tarjim.whole import whole

HEADROOM = 0.97
VOICE_GAIN = 1.0
FULL = 100  # dub.balance: the background at its own level, as it always was (2026-11-09)
MIN_ROOM = 0.3
GRACE = 0.25
EVEN_MOST = 2.0  # a line is made at most twice, or half, as loud


def tempo(line: Line, took: float) -> float:
    """Faster when the voice is longer than its room; slower when it ends before its speaker
    stops talking (as far as the pace allows)."""
    room = max(line.room, MIN_ROOM)
    if took > room:
        return took / room
    return took / line.talk if took < line.talk else 1.0


def place(track: np.ndarray, line: Line, wav: np.ndarray, pace: Pace = USUAL_PACE) -> None:
    if wav.size == 0:
        return
    voice = trim(wav)
    fitted = fit(speed_up(voice, tempo(line, voice.size / RATE), pace=pace),
                 max(line.room, MIN_ROOM) + GRACE)
    start = int(line.start * RATE)
    end = min(start + fitted.size, track.shape[0])
    if end > start:
        track[start:end] += fitted[:end - start, None] * VOICE_GAIN


def strength(wav: np.ndarray) -> float:
    voice = trim(wav)
    return float(np.sqrt(np.mean(voice**2))) if voice.size else 0.0


def evened(speech: list[np.ndarray]) -> list[np.ndarray]:
    """Each line as loud as the middle one, within EVEN_MOST: the voice says every line on its
    own, some louder than others, and one gain for the whole dub (loud.py) keeps them apart."""
    levels = [strength(wav) for wav in speech]
    heard = [found for found in levels if found > 0]
    if not heard:
        return speech
    middle = float(np.median(heard))
    return [wav * float(np.clip(middle / found, 1 / EVEN_MOST, EVEN_MOST)) if found > 0 else wav
            for wav, found in zip(speech, levels, strict=True)]


def mix(lines: list[Line], speech: list[np.ndarray], background: np.ndarray,
        pace: Pace = USUAL_PACE) -> np.ndarray:
    """The voices over the music and sound under them, as loud as the person's dub.balance
    keeps it; one balance, since the peak is brought to HEADROOM after (2026-11-09)."""
    from tarjim.prefs.active import active

    track = np.zeros_like(background)
    for line, wav in zip(lines, evened(speech), strict=True):
        place(track, line, wav, pace)
    balance = active().dub.balance
    track += background if balance == FULL else background * (balance / FULL)
    peak = float(np.max(np.abs(track))) if track.size else 0.0
    return track * (HEADROOM / peak) if peak > HEADROOM else track


def mux(picture: Path | None, sound: Path, target: Path) -> Path:
    """The dubbed sound on the picture, padded with silence so the picture's length decides where
    the video ends; a file with no picture is dubbed into sound alone. Both at the feed's level
    (loud.py)."""
    levelled = level(sound)
    sound_out = ["-ar", str(RATE), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    with whole(target) as part:
        if picture is None:
            ffmpeg(["-y", *source(sound), "-map", "0:a:0", "-af", levelled, *sound_out,
                    str(part)])
        else:
            ffmpeg(["-y", *source(picture), *source(sound), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-af", f"{levelled},apad", *sound_out, "-shortest",
                    str(part)])
    return target
