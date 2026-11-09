from typing import Any

import numpy as np

from tarjim.asr.ctc import BLANK, FRAME

THRESHOLD = 0.5
PAD = 0.1
SILENCE_PENALTY = 30.0
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


def mute(logp: np.ndarray, penalty: np.ndarray) -> np.ndarray:
    """Each frame's letters made less likely by its penalty, the blank never (2026-11-09: the
    three tiers of asr/speechmap.py; before, silence paid SILENCE_PENALTY and speech nothing)."""
    muted = logp.copy()
    letters = np.arange(logp.shape[1]) != BLANK
    muted[:, letters] -= penalty[:len(logp), None].astype(muted.dtype)
    return muted


def mute_silence(logp: np.ndarray, speech: np.ndarray) -> np.ndarray:
    return mute(logp, np.where(speech[:len(logp)], 0.0, SILENCE_PENALTY))
