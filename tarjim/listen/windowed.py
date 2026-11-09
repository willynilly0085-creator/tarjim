"""Each line's speaker from the voices of the clip's windows of steady talk (2026-11-09).

The voices come from listen/cluster.py and the changes of voice inside a label from
listen/changes.py. A segment of a label (all of it, or its part between two changes) goes to
the voice most of its windows are, and each voice keeps the name of the label most of its
windows were heard with, one name to one voice; a voice no name is left for (one the listener
never told apart, or the other side of a swap) gets a name nobody has. A line STEADY long or
more is then judged by its own windows too, and moves to another voice only when it is MARGIN
nearer to it than to its own without it (as listen/lined.judged); a line glimpsed once
(listen/turns.py) moves the same way by its one print. A shorter line, or one said
over another speaker, goes with its segment (its print says too little), or where its label's
heard lines on both sides of it were all moved to one speaker, with them. Nothing is moved when
the voices are not clearly apart: windows on average under SILHOUETTE nearer their own voice
than the next, or the lines' voices as listen/lined.unreliable finds them. Fewer than two
voices with ENOUGH_S of windows each is too little to tell: the line check decides then.
"""
from collections import defaultdict
from collections.abc import Callable
from functools import cache
from typing import NamedTuple

import numpy as np

from tarjim.listen.changes import Placer, Segment, cuts, homes, label_spans, segments
from tarjim.listen.cluster import (
    FEWEST,
    Voices,
    calibrated,
    centres,
    heard_voices,
    voices,
)
from tarjim.listen.cutpoint import Ears, placer
from tarjim.listen.follow import NEAREST, around
from tarjim.listen.gate import ENOUGH_S, doubt, enough, unit
from tarjim.listen.lined import MARGIN, Labels
from tarjim.listen.seams import grouped
from tarjim.listen.turns import Window
from tarjim.models import Word
from tarjim.speakers import Line, based, own_name, who


class Verdict(NamedTuple):
    """Each line's speaker by voice, or why none is moved; little when the clip has too little
    steady talk to tell voices apart by windows."""

    labels: Labels
    why: str
    little: bool
    note: str = ""


def names(v: Voices, ids: np.ndarray, taken: set[str]) -> dict[int, str]:
    """Each voice's name: the label most of its windows were heard with, one to one, else a
    name nobody has."""
    heard: dict[tuple[int, str], float] = defaultdict(float)
    first: dict[tuple[int, str], float] = defaultdict(lambda: np.inf)
    for k, window in enumerate(v.windows):
        pair = int(ids[k]), window.label
        heard[pair] += float(v.seconds[k])
        first[pair] = min(first[pair], window.start)
    # most seconds first; of two alike, the label heard first in the voice (before a swap)
    order = sorted(heard, key=lambda pair: (-heard[pair], first[pair], pair))
    found: dict[int, str] = {}
    for voice, label in order:
        if voice not in found and label not in found.values() and based(label):
            found[voice] = label
    for voice, label in order:
        if voice not in found:
            found[voice] = own_name(label, taken | set(found.values()))
    return found


def majority(items: list[Window], ids: list[int], of: dict[Line, Segment]) -> dict[Segment, int]:
    """The voice most of each segment's windows and glimpses are, by their seconds."""
    seconds: dict[Segment, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for item, voice in zip(items, ids, strict=True):
        seconds[of[item.line]][voice] += item.end - item.start
    return {segment: max(sorted(c), key=c.__getitem__) for segment, c in seconds.items()}


def moved(alike: np.ndarray, own: int) -> int:
    """Another voice when it is NEAREST alike or more and MARGIN nearer than own, else own."""
    best = int(np.argmax(alike))
    return best if alike[best] >= NEAREST and alike[best] - alike[own] >= MARGIN else own


def judged(v: Voices, ids: np.ndarray, own: dict[Line, int]) -> dict[Line, int]:
    """Each steady line's voice: its segment's, or another MARGIN nearer to its windows than its
    own voice is without them."""
    count = int(ids.max()) + 1
    sums = np.stack([v.vecs[ids == k].sum(axis=0) for k in range(count)])
    by_line: dict[Line, list[int]] = defaultdict(list)
    for k, window in enumerate(v.windows):
        by_line[window.line].append(k)
    found = {}
    for line, picked in by_line.items():
        voice, mine = unit(v.vecs[picked].sum(axis=0)), np.zeros_like(sums)
        np.add.at(mine, ids[picked], v.vecs[picked])
        found[line] = moved(np.array([float(voice @ unit(rest)) for rest in sums - mine]),
                            own[line])
    return found


def glanced(glimpses: list[Window], voices_at: np.ndarray, own: dict[Line, int]) -> dict[Line, int]:
    """Each glimpsed line's voice: its segment's, or another MARGIN nearer to its print."""
    return {g.line: moved(voices_at @ unit(g.vec), own[g.line]) for g in glimpses}


def with_short(words: list[Word], every: list[Window], labels: Labels) -> Labels:
    """The labels, each short line (no window, no glimpse) given the speaker its label's
    nearest heard lines on both sides (or the one side there is) were given, where they agree
    (as listen/follow.followed): a label heard in too few windows to see its change of voice
    still has its long lines moved, and its short lines go with them."""
    heard: dict[str, list[Line]] = defaultdict(list)
    for line in sorted({w.line for w in every}):
        heard[who(words[line[0]].speaker)].append(line)
    found = dict(labels)
    for line in labels:
        sides = around(line, heard[who(words[line[0]].speaker)])
        names = {labels[k] for k in sides}
        if line not in sides and len(names) == 1:
            found[line] = names.pop()
    return found


def grown_voices(words: list[Word], windows: list[Window]) -> tuple[Voices, np.ndarray]:
    """The windows as arrays, grouped by label and its seams, and the voice of each."""
    v = voices(windows, [w.label for w in windows])
    join = calibrated(v)
    v = v._replace(groups=grouped(words, v, label_spans(words), join))
    return v, heard_voices(v, join)


class Heard(NamedTuple):
    """The windows of the clip's steady talk, the glimpses of its other lines (listen/turns.py)
    and the print of any stretch of it."""

    windows: list[Window]
    glimpses: list[Window]
    hear: Callable[[float, float], np.ndarray]


def placers(words: list[Word], ears: Ears) -> Callable[[str], Placer]:
    """Where each label is cut where its voice changes (listen/cutpoint.py)."""
    spans = label_spans(words)
    return lambda label: placer(spans[label], ears)


def parted(words: list[Word], heard: Heard, v: Voices,
           ids: np.ndarray) -> tuple[dict[Line, Segment], list[Window], list[int]]:
    """The lines in their labels' segments, with the windows and glimpses (each in its part of
    its line) and the voice of each."""
    voices_at = centres(v, ids, int(ids.max()) + 1)
    every = heard.windows + heard.glimpses
    near = [int(np.argmax(voices_at @ unit(g.vec))) for g in heard.glimpses]
    every_ids = ids.tolist() + near
    ears = Ears(voices_at, cache(heard.hear))
    of = segments(words, cuts(every, every_ids, placers(words, ears)))
    return of, homes(words, every, of), every_ids


def decided(words: list[Word], heard: Heard) -> Verdict:
    """Each line's speaker by the voices of the clip's windows, or why not."""
    if len({w.label for w in heard.windows}) < FEWEST:
        return Verdict({}, "too little steady talk of two labels", True)
    v, ids = grown_voices(words, heard.windows)
    if not enough(v, ids):
        return Verdict({}, f"fewer than two voices with {ENOUGH_S:.0f} s of steady talk", True)
    of, every, every_ids = parted(words, heard, v, ids)
    v = v._replace(windows=every[:len(ids)])
    voice_of = majority(every, every_ids, of)
    own = {line: voice_of[segment] for line, segment in of.items() if segment in voice_of}
    voices_at = centres(v, ids, int(ids.max()) + 1)
    found = own | judged(v, ids, own) | glanced(every[len(ids):], voices_at, own)
    named = names(v, ids, {label for label, _ in of.values()})
    labels = with_short(words, every, {line: named[voice] for line, voice in found.items()})
    note = (f"{len(ids)} windows in {int(ids.max()) + 1} voices, {len(every) - len(ids)} "
            f"glimpses, {sum(1 for s in set(of.values()) if s[1])} changes inside a label")
    return Verdict(labels, doubt(v, ids, labels), False, note)
