"""Synthetic voices for the voice-check tests (2026-11-09): 256 numbers a print like WeSpeaker's,
each window's print its voice plus noise, so two windows of one voice are about 0.72 alike (as
measured on the bench's clips) and two of different voices about 0."""
from typing import NamedTuple

import numpy as np
import pytest

from tarjim.asr import voiceprint
from tarjim.models import Word

SIZE = 256
NOISE = 0.62  # 1 / (1 + 0.62**2) = 0.72: how alike two windows of one voice are
WORD = 0.5  # seconds a word lasts


class Turn(NamedTuple):
    start: float
    seconds: float
    voice: str  # who truly speaks
    label: str  # who the listener said


def unit(vector: np.ndarray) -> np.ndarray:
    found: np.ndarray = vector / np.linalg.norm(vector)
    return found


def people(names: str, seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {name: unit(rng.normal(size=SIZE)) for name in names}


def alike_to(voice: np.ndarray, cosine: float, seed: int) -> np.ndarray:
    """Another voice this alike to voice."""
    other = unit(np.random.default_rng(seed).normal(size=SIZE))
    other = unit(other - (other @ voice) * voice)
    return unit(cosine * voice + np.sqrt(1 - cosine**2) * other)


def words_of(turns: list[Turn]) -> list[Word]:
    found = []
    for turn in turns:
        count = max(1, round(turn.seconds / WORD))
        step = turn.seconds / count
        found += [Word("w", turn.start + k * step, turn.start + (k + 1) * step, turn.label)
                  for k in range(count)]
    return sorted(found, key=lambda w: w.start)


def sound(seconds: float) -> np.ndarray:
    """Each sample holds its own time, so a stretch tells where it starts."""
    return np.arange(int(seconds * voiceprint.RATE)) / voiceprint.RATE


def heard(monkeypatch: pytest.MonkeyPatch, turns: list[Turn], voices: dict[str, np.ndarray],
          noise: float = NOISE) -> list[Word]:
    """The words of the turns, with voiceprint.print_of giving each stretch the print of the
    voice said most of it (the one its middle is nearest) plus noise of its own (the same for
    the same stretch)."""
    def print_of(clip: np.ndarray) -> np.ndarray:
        start, middle = float(clip[0]), float(clip[len(clip) // 2])
        turn = min(turns, key=lambda t: max(t.start - middle, 0.0,
                                            middle - t.start - t.seconds))
        rng = np.random.default_rng(round(start * 100))
        return unit(voices[turn.voice] + noise * unit(rng.normal(size=SIZE)))

    monkeypatch.setattr(voiceprint, "print_of", print_of)
    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    return words_of(turns)


def by_turns(count: int, names: str, seconds: float = 4.0, pause: float = 0.6) -> list[Turn]:
    """count turns, the names taking them in order, each heard with its own name."""
    return [Turn(k * (seconds + pause), seconds, names[k % len(names)],
                 f"S{names.index(names[k % len(names)]) + 1}") for k in range(count)]


def relabelled(turns: list[Turn], labels: dict[int, str]) -> list[Turn]:
    return [t._replace(label=labels.get(k, t.label)) for k, t in enumerate(turns)]


def spoken(words: list[Word], turns: list[Turn]) -> list[str]:
    """The speaker of each turn's first word."""
    return [next(w.speaker for w in words if abs(w.start - t.start) < 1e-6) for t in turns]


def end(turns: list[Turn]) -> float:
    return max(t.start + t.seconds for t in turns) + 1.0

