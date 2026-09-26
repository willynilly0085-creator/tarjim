from typing import Any

import numpy as np

from tarjim.asr.ctc import BLANK, FRAME

THRESHOLD = 0.5
PAD = 0.1
SILENCE_PENALTY = 30.0
BLANK_IN_SPEECH = 0.0
MIN_SILENCE_MS = 150
MIN_SPEECH_MS = 100


def speech_regions(wav: Any) -> list[tuple[float, float]]:
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad

    stamps = get_speech_timestamps(
        torch.from_numpy(np.asarray(wav, dtype=np.float32)), load_silero_vad(),
        threshold=THRESHOLD, min_silence_duration_ms=MIN_SILENCE_MS,
        min_speech_duration_ms=MIN_SPEECH_MS, speech_pad_ms=0, return_seconds=True)
    return [(float(s["start"]), float(s["end"])) for s in stamps]


def speech_mask(regions: list[tuple[float, float]], frames: int) -> np.ndarray:
    mask = np.zeros(frames, dtype=bool)
    for start, end in regions:
        mask[max(0, int((start - PAD) / FRAME)):int((end + PAD) / FRAME) + 1] = True
    return mask


def mute_silence(logp: np.ndarray, speech: np.ndarray) -> np.ndarray:
    muted = logp.copy()
    silent = ~speech[:len(logp)]
    letters = np.arange(logp.shape[1]) != BLANK
    muted[np.ix_(silent, letters)] -= SILENCE_PENALTY
    muted[~silent, BLANK] -= BLANK_IN_SPEECH
    return muted
