"""Where in a change of voice the label is cut (2026-11-09).

Between the last window of one voice and the first of the next the label may have several
pauses (PAUSE or more), and between them runs of its words too short to be heard in windows of
their own, or the end of a line the listener ran on. The widest pause is not always the change:
on the bench a short "Let us talk about cost." before the swap went with the voice after it. So
each run of the label's words between two of those pauses, LEANS long or more, is printed whole,
and the cut goes in the pause that leaves the most of that lean on its own side, each run's lean
counted by its seconds (a 0.3 s print leans the right way on every bench clip, but by less, so
it only decides where nothing longer does). Where nothing leans, the widest pause: a label's
long pauses are where the other people talk.

A pause is a place for the cut when any of it falls where the change can be: on the bench the
label's pause where the swap was began at its last line before the other people's turns, before
the window the other label's change leaves (listen/changes.narrowed), and the cut went in the
0.9 s pause after the swap's first short line instead, keeping that line with the wrong voice.
"""
from collections.abc import Callable
from itertools import pairwise
from typing import NamedTuple

import numpy as np

from tarjim.listen.changes import PAUSE, Placer, Spans

Gap = tuple[float, float]
LEANS = 0.3  # seconds: a run of words shorter than this is not printed to lean the cut


class Ears(NamedTuple):
    """Each voice's centre (rows, length one) and the print of a stretch of the clip."""

    voices: np.ndarray
    hear: Callable[[float, float], np.ndarray]


def gaps(spans: Spans, first: float, last: float) -> list[Gap]:
    """The label's pauses PAUSE long or more with any of them between first and last."""
    return [(a[1], b[0]) for a, b in pairwise(spans)
            if b[0] - a[1] >= PAUSE and a[1] < last and b[0] > first]


def runs(found: list[Gap]) -> Spans:
    """The label's words between each two neighbouring pauses, as (start, end)."""
    return [(a[1], b[0]) for a, b in pairwise(found)]


def leaning(ears: Ears, inside: Spans, sides: tuple[int, int]) -> list[tuple[Gap, float]]:
    """Each run LEANS long or more and how much nearer it sounds to the voice before than to
    the voice after, times its seconds."""
    before, after = ears.voices[sides[0]], ears.voices[sides[1]]
    found = []
    for begin, end in (s for s in inside if s[1] - s[0] >= LEANS):
        voice = ears.hear(begin, end)
        voice = voice / (np.linalg.norm(voice) or 1.0)
        found.append(((begin, end), float(voice @ before - voice @ after) * (end - begin)))
    return found


def kept(gap: Gap, leans: list[tuple[Gap, float]]) -> float:
    """How much of the lean a cut in the gap leaves on its own side."""
    return sum(lean if run[1] <= gap[0] else -lean for run, lean in leans)


def placer(spans: Spans, ears: Ears) -> Placer:
    """Where one label (its words' spans, in order) is cut between first and last, from the
    voice sides[0] to sides[1]: None where it has no pause there."""

    def place(first: float, last: float, sides: tuple[int, int]) -> float | None:
        found = gaps(spans, first, last)
        if not found:
            return None
        leans = leaning(ears, runs(found), sides)
        best = max(found, key=lambda g: (round(kept(g, leans), 6), g[1] - g[0], -g[0]))
        return (best[0] + best[1]) / 2

    return place
