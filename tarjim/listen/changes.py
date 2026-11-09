"""Where one label changes voice (2026-11-09).

On 2026-11-06 the listener swapped host and guest after a pause, and every line from there on
wore the other's label. A label is read here as its windows in time order, each with the voice
it is nearest (listen/cluster.py). Where most of RUN to SIDE windows (RUN_S long or more) are
one voice and most of those after them another, the windows on each side of the change
included, the label changes voice there: one window heard nearer the wrong voice neither makes
a change nor hides one. SPLITS at most in one label, the clearest first. A swap is one moment
for both labels, so the cut is looked for first where the other labels' changes of voice leave
it, then between the two windows: the pause (PAUSE or more) of the label's words that the short
lines there lean to (listen/cutpoint.py), so they go with the side they are said on; a turn the
listener ran on into the next person's under one label (a pause under a second makes one line)
is cut there too. The words after a cut are a part of the label of their own, which goes to its
own voice (listen/windowed.py).
"""
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import NamedTuple

from tarjim.listen.turns import Window
from tarjim.models import Word
from tarjim.speakers import Line, lines, who

RUN = 3  # windows on each side of a change, at least, most of them one voice
SIDE = 5  # windows on each side of a change looked at
RUN_S = 4.0  # seconds those windows span, at least
SPLITS = 2  # changes in one label, at most
PAUSE = 0.25  # seconds: a change of voice is cut only at a pause this long or longer

Segment = tuple[str, int]  # a label and how many of its changes come before
Spans = list[tuple[float, float]]
# where a label is cut between two times, from one voice to another (None: no pause there)
Placer = Callable[[float, float, tuple[int, int]], float | None]


def one_voice(part: Sequence[Window], ids: Sequence[int], edge: int) -> int | None:
    """The voice most of RUN windows or more are (RUN_S long or more), when the window at the
    change (edge) is that voice too, else None."""
    if len(part) < RUN or part[-1].end - part[0].start < RUN_S:
        return None
    voice, count = Counter(ids).most_common(1)[0]
    return voice if count * 2 > len(ids) and voice == edge else None


def strength(ids: Sequence[int], at: int) -> int:
    """How many of the SIDE windows on both sides of a change agree with their side."""
    before, after = ids[max(0, at - SIDE):at], ids[at:at + SIDE]
    return before.count(ids[at - 1]) + after.count(ids[at])


def changes(order: Sequence[Window], ids: Sequence[int],
            paused: Callable[[int], bool] = lambda _at: True) -> list[int]:
    """Where in one label's windows (in time order) its voice changes, at a pause (paused),
    SPLITS at most, the clearest first, each between parts mostly of two voices."""
    found = []
    for at in range(RUN, len(order) - RUN + 1):
        start = max(0, at - SIDE)
        before = one_voice(order[start:at], ids[start:at], ids[at - 1])
        after = one_voice(order[at:at + SIDE], ids[at:at + SIDE], ids[at])
        if None not in (before, after) and before != after and paused(at):
            found.append((-strength(list(ids), at), at))
    kept: list[int] = []
    for _, at in sorted(found):
        if len(kept) < SPLITS and distinct(list(ids), sorted([*kept, at])):
            kept.append(at)
    return sorted(kept)


def distinct(ids: list[int], at: list[int]) -> bool:
    """Whether every two neighbouring parts the cuts make are mostly two voices, RUN windows
    or more each."""
    bounds = [0, *at, len(ids)]
    parts = [ids[a:b] for a, b in pairwise(bounds)]
    voices = [Counter(part).most_common(1)[0][0] for part in parts if len(part) >= RUN]
    return len(voices) == len(parts) and all(a != b for a, b in pairwise(voices))


def cut(spans: Spans, first: float, last: float) -> float | None:
    """The middle of the widest pause (PAUSE or more) between the label's words (spans, in
    order) from first to last, or None when they have none."""
    inside = [s for s in spans if s[1] >= first and s[0] <= last]
    gaps = [(b[0] - a[1], (a[1] + b[0]) / 2) for a, b in pairwise(inside)]
    widest = max(gaps, default=(0.0, None))
    return widest[1] if widest[0] >= PAUSE else None


class Change(NamedTuple):
    """One label's change of voice: between first and last, from the voice sides[0] to
    sides[1]."""

    label: str
    first: float
    last: float
    sides: tuple[int, int]


def label_changes(label: str, order: list[Window], ids: list[int], place: Placer) -> list[Change]:
    """Where one label (its windows in time order and their voices) changes voice, at a
    pause place finds."""
    def at(k: int) -> Change:
        return Change(label, order[k - 1].start, order[k].end, (ids[k - 1], ids[k]))

    def paused(k: int) -> bool:
        return place(*at(k)[1:]) is not None

    return [at(k) for k in changes(order, ids, paused)]


def narrowed(change: Change, every: list[Change]) -> Change:
    """The change between first and last that other labels' changes of voice there leave: a swap
    of two labels is one moment for both, so the lines of one that fall before the other's
    change go with the voice before."""
    first, last = change.first, change.last
    for other in every:
        if other.label != change.label and other.first < last and other.last > first:
            first, last = max(first, other.first), min(last, other.last)
    return change._replace(first=first, last=last)


def by_label(windows: list[Window]) -> dict[str, list[int]]:
    """Each label's windows, by their place in windows, in time order."""
    found: dict[str, list[int]] = defaultdict(list)
    for k, window in enumerate(windows):
        found[window.label].append(k)
    return {label: sorted(picked, key=lambda k: windows[k].start)
            for label, picked in found.items()}


def label_spans(words: list[Word]) -> dict[str, Spans]:
    """Each label's words, as (start, end) in time order."""
    found: dict[str, Spans] = defaultdict(list)
    for word in sorted(words, key=lambda w: w.start):
        found[who(word.speaker)].append((word.start, word.end))
    return found


def cuts(windows: list[Window], ids: Sequence[int],
         place_for: Callable[[str], Placer]) -> dict[str, list[float]]:
    """The times each label changes voice at, each label cut where its placer puts it: in the
    time other labels' changes leave it (narrowed) where it has a pause there."""
    every = [change for label, picked in by_label(windows).items()
             for change in label_changes(label, [windows[k] for k in picked],
                                         [ids[k] for k in picked], place_for(label))]
    found: dict[str, list[float]] = {label: [] for label in by_label(windows)}
    for change in every:
        place = place_for(change.label)
        when = place(*narrowed(change, every)[1:])
        when = place(*change[1:]) if when is None else when
        found[change.label] += [] if when is None else [when]
    return {label: sorted(times) for label, times in found.items()}


def parted(words: list[Word], line: Line, times: list[float]) -> list[Line]:
    """The line in parts, cut at the times."""
    found, first = [], line[0]
    for k in range(line[0] + 1, line[1]):
        if bisect_right(times, words[k].start) != bisect_right(times, words[k - 1].start):
            found.append((first, k))
            first = k
    return [*found, (first, line[1])]


def segments(words: list[Word], times: dict[str, list[float]]) -> dict[Line, Segment]:
    """Each line with a speaker, cut where its label changes voice, as its label's segment: how
    many of the label's changes come before it."""
    found = {}
    for line in lines(words):
        label = who(words[line[0]].speaker)
        for part in parted(words, line, times.get(label, [])) if label else []:
            found[part] = (label, bisect_right(times.get(label, []), words[part[0]].start))
    return found


def home(words: list[Word], window: Window, parts: list[Line]) -> Line:
    """The part of its line a window is in: the one its middle is said in, else the nearest."""
    middle = (window.start + window.end) / 2
    return min(parts, key=lambda p: (max(words[p[0]].start - middle, 0.0,
                                         middle - words[p[1] - 1].end), p))


def homes(words: list[Word], windows: list[Window], of: dict[Line, Segment]) -> list[Window]:
    """The windows, each with the part of its line it is in (of: the parts) for its line."""
    parts = sorted(of)
    firsts = [part[0] for part in parts]
    return [w._replace(line=home(words, w, parts[bisect_left(firsts, w.line[0]):
                                                  bisect_left(firsts, w.line[1])]))
            for w in windows]
