"""Long sound is heard in pieces of about three minutes (the forced aligner takes five at most),
each cut at the quietest tenth of a second within five seconds of the three-minute mark. The
pieces put back together are the whole sound, sample for sample; a piece shorter than half a
second is padded with silence at its end. The same cuts the qwen-asr package made
(inference/utils.py).
"""
from dataclasses import dataclass
from itertools import pairwise

import numpy as np

RATE = 16000
LONGEST = 180.0
SEARCH = 5.0
WINDOW = 0.1
SHORTEST = 0.5


@dataclass(frozen=True)
class Piece:
    wav: np.ndarray
    offset: float


def quietest(wav: np.ndarray, cut: int, start: int) -> int:
    reach, window = int(SEARCH * RATE), max(4, int(WINDOW * RATE))
    left, right = max(start, cut - reach), min(len(wav), cut + reach)
    if right - left <= window:
        return cut
    loudness = np.abs(wav[left:right])
    sums = np.convolve(loudness, np.ones(window, dtype=np.float32), mode="valid")
    begin = int(np.argmin(sums))
    return left + begin + int(np.argmin(loudness[begin:begin + window]))


def boundaries(wav: np.ndarray) -> list[int]:
    most, start, cuts = int(LONGEST * RATE), 0, [0]
    while len(wav) - start > most:
        start = min(max(quietest(wav, start + most, start), start + 1), len(wav))
        cuts.append(start)
    return [*cuts, len(wav)]


def padded(wav: np.ndarray) -> np.ndarray:
    short = int(SHORTEST * RATE) - len(wav)
    return np.pad(wav, (0, short)).astype(np.float32) if short > 0 else wav


def pieces(wav: np.ndarray) -> list[Piece]:
    wav = np.asarray(wav, dtype=np.float32)
    cuts = boundaries(wav)
    return [Piece(padded(wav[a:b]), a / RATE) for a, b in pairwise(cuts)]
