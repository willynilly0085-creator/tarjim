"""How far the tolerant aligner (asr/tolerant.py) may stray from the text on one clip.

Measured on the clip's own sound, on the runs the strict check finds said where they are timed
(agree.FOUND): on their letter frames, how far the said letter sits below the clip's loudest
letter. The star (sound the text does not hold) is priced that far below the loudest letter, plus
a margin. On peaky letters that spread is about nothing, so the floor holds almost always; the
spread is reported (scripts/synth/decode_bench.py) rather than trusted to set the star
(2026-11-08). With too few runs found (a chant, music, letters a script reads poorly), there is
nothing to measure, and with many letters heard inside the found runs that their text does not
explain (letters lost or wrong in reading the script, two voices at once) the letters cannot be
trusted to tell a word not said: either way the aligner stays strict, no star and no skip.
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from tarjim.asr.agree import FOUND
from tarjim.asr.ctc import BLANK, FRAME, token_spans
from tarjim.asr.letters import Key

STAR_ENTER = 2.0  # nats, paid once on entering the star
SKIP_BASE = 5.0  # nats for stepping over a word the sound does not hold
SKIP_PER_TOKEN = 2.5  # and per letter of it, so a long word is never cheaper to step over
# Measured 2026-11-08 (decode_bench.py, 18 clips, a line from another clip put in for 5% of the
# words): words not said left out 92%, words said left out 0.37% (worst clip 3.2%). Grid of base
# {4, 5, 6, 8} x per letter {2, 2.5, 3}: dearer prices leave out fewer words said and also fewer
# words not said; no setting wins on both, so the planned prices stay.
MIN_RUNS = 12  # runs found by the strict check, below which the aligner stays strict
MIN_FRAMES = 200  # letter frames in them, likewise
# letters heard inside found runs that the text does not explain, above which the letters are
# not trusted (2026-11-08, scripts/synth/decode_bench.py on 18 clips): clean text 0.010-0.081;
# two voices over each other 0.22; 60% of the letters dropped (kanji read as pinyin) >= 0.53;
# 30% wrong >= 0.28. With either spoilt reading the skip left out 8-20% of the words said.
UNEXPLAINED = 0.15
SHARE = 80  # the percentile of the spread the star is priced at
MARGIN = 1.0
FLOOR, CEILING = 1.0, 6.0  # nats below the loudest letter the star may sit


@dataclass(frozen=True)
class Costs:
    """The tolerant aligner's prices; a star_delta of None turns the star and the skip off."""
    star_delta: float | None
    star_enter: float = STAR_ENTER
    skip: bool = False
    skip_base: float = SKIP_BASE
    skip_per_token: float = SKIP_PER_TOKEN

    @property
    def star(self) -> bool:
        return self.star_delta is not None

    @property
    def skipping(self) -> bool:
        return self.skip and self.star

    def skip_cost(self, tokens: int) -> float:
        return self.skip_base + self.skip_per_token * tokens


@dataclass(frozen=True)
class Run:
    """A run's letters and the frames it is looked for in (as agree.run_score does)."""
    tokens: list[int]
    low: int
    high: int


@dataclass(frozen=True)
class Gaps:
    """What was measured: runs found, their letter frames and the spread (p50, p80, p95, max)
    of the loudest letter above the said one there, and the share of the letters heard inside
    the runs that the text does not explain."""
    runs: int
    frames: int
    spread: dict[str, float] = field(default_factory=dict)
    unexplained: float = 0.0


class Found(NamedTuple):
    gaps: NDArray[np.float64]  # per letter frame
    peaks: int  # frames inside the run that a letter is the loudest on
    unexplained: int  # of them, frames where it is not the text's own letter


def letter_gaps(logp: NDArray[np.floating], run: Run) -> Found | None:
    """The loudest letter above the said one on each of the run's letter frames, and the run's
    letter peaks the text does not explain; None for a run the strict check does not find."""
    sound = logp[run.low:run.high]
    spans = token_spans(sound, run.tokens) if run.tokens else None
    if spans is None or np.mean([score for *_, score in spans]) < FOUND:
        return None
    said = np.full(len(sound), -1)
    for (start, end, _), token in zip(spans, run.tokens, strict=True):
        said[round(start / FRAME):round(end / FRAME)] = token
    inside = slice(round(spans[0][0] / FRAME), round(spans[-1][1] / FRAME))
    loudest = sound.argmax(axis=1)[inside]
    peaks = loudest != BLANK
    rows = np.flatnonzero(said >= 0)
    gaps = np.delete(sound[rows], BLANK, axis=1).max(axis=1) - sound[rows, said[rows]]
    return Found(gaps.astype(np.float64), int(peaks.sum()),
                 int((peaks & (loudest != said[inside])).sum()))


def measured(logp: NDArray[np.floating], runs: list[Run]) -> Gaps:
    found = [g for g in (letter_gaps(logp, run) for run in runs) if g is not None]
    if not found:
        return Gaps(0, 0)
    gaps = np.concatenate([f.gaps for f in found])
    shares = {"p50": 50, f"p{SHARE}": SHARE, "p95": 95, "max": 100}
    spread = {name: round(float(np.percentile(gaps, q)), 3) for name, q in shares.items()}
    peaks = sum(f.peaks for f in found)
    unexplained = sum(f.unexplained for f in found) / peaks if peaks else 0.0
    return Gaps(len(found), len(gaps), spread, round(unexplained, 4))


def delta_of(gaps: Gaps, margin: float = MARGIN) -> float | None:
    if gaps.runs < MIN_RUNS or gaps.frames < MIN_FRAMES or gaps.unexplained > UNEXPLAINED:
        return None
    return float(np.clip(gaps.spread[f"p{SHARE}"] + margin, FLOOR, CEILING))


def calibrated(logp: NDArray[np.floating], runs: list[Run], skip: bool = False) -> Costs | None:
    """The clip's prices; None, so the aligner stays strict, when too few runs are found."""
    delta = delta_of(measured(logp, runs))
    return None if delta is None else Costs(delta, skip=skip)


@dataclass(frozen=True)
class Calibration:
    """What one clip was measured to allow: the prices (None: strict), and the score below
    which a run is taken for not said where it is timed (agree.clip_baseline)."""
    costs: Costs | None
    baseline: float


class Calibrations:
    """One clip's calibration, made once and kept for that clip alone, as its letters are
    (asr/letters.Letters): every timing of the clip, a stretch of it included, prices its
    letters alike (2026-11-09)."""

    def __init__(self) -> None:
        self.last: tuple[Key, Calibration] | None = None
        self.made = 0  # clips measured, for the tests

    def __call__(self, key: Key, make: Callable[[], Calibration]) -> Calibration:
        if self.last is None or self.last[0] != key:
            self.last = None
            self.last = (key, make())
            self.made += 1
        return self.last[1]
