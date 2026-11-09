"""Where a label's own windows say its voice changes, before any voice is known (2026-11-09).

A label swapped half way through is half one voice and half the other, and so is the label it
was swapped with: their averages are alike, and no window is nearer one than the other, so
voices grown from the labels never come apart (a panel's two speakers swapped at the middle
stayed swapped). So each label is first read alone: where the SIDE windows before a pause and
the SIDE after it are not one voice together (under the clip's join across) but each side is
(nearer join within than the two sides are), the label is two groups from there, SPLITS at
most, the clearest first. The groups, not the labels, are where the clip's voices are grown from
(listen/cluster.py); which name each part keeps is decided after (listen/changes.py).
"""
from tarjim.listen.changes import RUN, SIDE, SPLITS, Spans, by_label, cut, homes, segments
from tarjim.listen.cluster import Voices, alike, inner
from tarjim.models import Word


def apart(v: Voices, order: list[int], at: int, join: float) -> float | None:
    """How alike the windows on the two sides of at are, when they are not one voice (under
    join) and each side is RUN windows or more of one (nearer join within than that across),
    else None."""
    before, after = order[max(0, at - SIDE):at], order[at:at + SIDE]
    if min(len(before), len(after)) < RUN:
        return None
    across = alike(v, before, after)
    within = min(inner(v, before), inner(v, after))
    return across if across < join and within >= (join + across) / 2 else None


def seams(v: Voices, order: list[int], spans: Spans, join: float) -> list[float]:
    """The times one label's windows (order, in time order) change voice, at pauses."""
    found = []
    for at in range(RUN, len(order) - RUN + 1):
        score = apart(v, order, at, join)
        when = cut(spans, v.windows[order[at - 1]].start, v.windows[order[at]].end)
        if score is not None and when is not None:
            found.append((score, at, when))
    kept: list[tuple[int, float]] = []
    for _, at, when in sorted(found):
        if len(kept) < SPLITS and all(abs(at - other) >= SIDE for other, _ in kept):
            kept.append((at, when))
    return sorted(when for _, when in kept)


def grouped(words: list[Word], v: Voices, spans: dict[str, Spans], join: float) -> list[str]:
    """Each window's group: its label, or its label's part after a seam ("1@S2")."""
    times = {label: seams(v, order, spans[label], join)
             for label, order in by_label(v.windows).items()}
    of = segments(words, times)
    named = {part: label if k == 0 else f"{k}@{label}" for part, (label, k) in of.items()}
    return [named[w.line] for w in homes(words, v.windows, of)]
