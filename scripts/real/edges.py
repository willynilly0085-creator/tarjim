"""Where the speech of one recording begins and ends inside it, measured twice: by its loudness
against its own room noise, and by the voice detector. An edge the two put more than AGREE apart
is unsure, and no timing is scored on it (build.py)."""
from typing import Any

import numpy as np
from paths import RATE, prepare

prepare()

from tarjim.asr.vad import speech_regions  # noqa: E402

HOP = RATE // 100
ABOVE = 12.0  # dB over a recording's room noise (its quietest tenth) that is speech
UNDER = 30.0  # ...and no more than this under its loudest frame
RUN = 3  # frames in a row over the bar before speech has begun, or has not yet ended
AGREE = 0.15  # seconds the loudness and the voice detector may differ on an edge


def levels(mono: np.ndarray) -> np.ndarray:
    frames = mono[:len(mono) // HOP * HOP].reshape(-1, HOP).astype(np.float64)
    return np.asarray(20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9))


def by_loudness(voice: np.ndarray) -> tuple[float, float]:
    """Where the speech begins and ends in a trimmed recording, by its loudness."""
    loud = levels(voice)
    bar = max(float(np.percentile(loud, 10)) + ABOVE, float(loud.max()) - UNDER)
    over = np.convolve(loud > bar, np.ones(RUN), mode="valid") == RUN
    runs = np.flatnonzero(over)
    return float(runs[0] * HOP / RATE), float((runs[-1] + RUN) * HOP / RATE)


def edges(voice: np.ndarray) -> dict[str, Any]:
    """The speech's start and end in the recording, and whether each is sure."""
    low, high = by_loudness(voice)
    regions = speech_regions(voice)
    first, last = (regions[0][0], regions[-1][1]) if regions else (-1.0, -1.0)
    return {"low": low, "high": high, "sure_start": abs(first - low) <= AGREE,
            "sure_end": abs(last - high) <= AGREE}
