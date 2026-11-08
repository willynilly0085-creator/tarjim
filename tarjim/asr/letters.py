"""The whole clip's letters, heard once: a stretch of it and the check after timing read theirs
from them (2026-11-08)."""
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from tarjim.asr.ctc import EPSILON, FRAME

Key = tuple[int, int, bytes]


def fingerprint(wav: Any) -> Key:
    """The same sound: the same array, length and samples taken across it."""
    samples = np.asarray(wav, dtype=np.float32)
    return id(wav), len(samples), samples[:: max(1, len(samples) // 64)].tobytes()


@dataclass(frozen=True)
class Piece:
    """A stretch of a longer sound that knows where it sits in it, so its letters are read from
    the whole sound's, heard once, and the stretch is never heard again (2026-11-08)."""
    clip: Any
    rate: int
    first: int  # the whole sound's frame it starts on
    past: int  # the frame it ends before

    @property
    def start(self) -> float:
        return self.first * FRAME

    def sound(self) -> Any:
        hop = self.rate * FRAME
        return self.clip[round(self.first * hop):round(self.past * hop)]

    def __len__(self) -> int:
        return len(self.sound())

    def __getitem__(self, key: Any) -> Any:
        return self.sound()[key]

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        return np.asarray(self.sound(), dtype=dtype)


def piece(clip: Any, rate: int, low: float, high: float) -> Piece:
    """The sound from low to high seconds, widened to whole frames of the clip."""
    return Piece(clip, rate, int(max(0.0, low) / FRAME + EPSILON),
                 math.ceil(high / FRAME - EPSILON))


class Letters:
    """The letters heard in one whole sound, kept for that sound alone, so a weak computer holds
    one clip's (about 45 MB for two hours) and a slice or a check never hears it again."""

    RECENT = 8  # sounds whose passes are counted; a few bytes each, so memory stays bounded

    def __init__(self, hear: Callable[[Any], np.ndarray]) -> None:
        self.hear = hear
        self.last: tuple[Key, np.ndarray] | None = None
        self.total = 0  # whole sounds heard
        self.since: dict[Key, int] = {}  # each recent sound: the passes before it was first heard

    def __call__(self, wav: Any) -> np.ndarray:
        if isinstance(wav, Piece):
            return self(wav.clip)[wav.first:wav.past]
        key = fingerprint(wav)
        if self.last is None or self.last[0] != key:
            self.last = None  # the clip before is let go before the next is heard
            self.last = (key, self.hear(wav))
            self.counted(key)
        return self.last[1]

    def counted(self, key: Key) -> None:
        self.since.setdefault(key, self.total)
        self.total += 1
        while len(self.since) > self.RECENT:
            del self.since[next(iter(self.since))]

    def count(self, wav: Any) -> int:
        """Every pass since this clip was first heard, a slice heard on its own included: once is
        right. Told once a run (listen/settle.py), not after each timing (2026-11-08)."""
        key = fingerprint(wav)
        return self.total - self.since[key] if key in self.since else 0
