"""The voices in a clip, from the windows of its steady talk (listen/turns.py, 2026-11-09).

Each label the listener gave (or its part, listen/seams.py) starts as one voice, and two voices
whose windows are alike on average (average linkage on cosine) become one, the most alike
first, while they are alike by `join` or more. `join` is measured on the clip itself: halfway
between how alike two windows of one turn are (p25) and how alike two windows of two labels are
(p75), never under JOIN_LOW or over JOIN_HIGH. Two voices said by turns under two labels (a
window of one between two of the other's, NEAR_S apart at most) were told apart by the listener
as it heard them, so they become one only when alike by APART_JOIN: measured 2026-11-09 on the
bench's clips, two halves of one voice are 0.67 to 0.77 alike on average and two people 0.37 at
most, so a listener's fake split still joins (the 0.85 first planned never would). A line only
another pass or request heard ("S2~p3", "S1~x4") is no such evidence. Then each window goes to
the voice it is nearest, again until nothing moves (ROUNDS), and windows FAR_S long or more near
no voice (under follow.NEAREST), and one voice among themselves, are one more voice: a person
the listener gave another's label. The voices that leaves are joined again the same way: a voice
the windows of a swapped label left in two (one before the swap, one after, never by turns)
becomes one.
"""
from typing import NamedTuple

import numpy as np

from tarjim.listen.follow import NEAREST
from tarjim.listen.turns import WINDOW, Window
from tarjim.speakers import REQUEST

NEAR_S = 60.0  # seconds: labels whose lines take turns this close are one request's two people
NEXT = 2  # turns: a label's turns this near are one voice when no turn has two windows
JOIN_LOW, JOIN_HIGH = 0.45, 0.75  # the clip's own join is kept between these
APART_JOIN = 0.65  # labels heard by turns join only this alike (measured 2026-11-09)
FAR_S = 10.0  # seconds of windows near no voice that make one more
ROUNDS = 5  # times the windows go to their nearest voice, at most
MORE = 3  # voices found that way, at most
FEWEST = 2  # voices: one is never apart from another
QUARTER, THREE_QUARTERS = 25, 75

Pairs = set[frozenset[int]]


class Voices(NamedTuple):
    """The windows as arrays: prints, how alike each two are, their seconds, lines and groups."""

    vecs: np.ndarray
    sims: np.ndarray
    seconds: np.ndarray
    windows: list[Window]
    groups: list[str]


def voices(windows: list[Window], groups: list[str]) -> Voices:
    vecs = np.stack([w.vec / (np.linalg.norm(w.vec) or 1.0) for w in windows])
    return Voices(vecs, vecs @ vecs.T, np.array([w.end - w.start for w in windows]),
                  windows, groups)


def turn_of(v: Voices) -> np.ndarray:
    """Each window's turn: the place of its line among the lines heard in windows, in time."""
    firsts = {line: start for start, line in sorted((w.start, w.line) for w in v.windows)[::-1]}
    order = {line: k for k, line in enumerate(sorted(firsts, key=firsts.__getitem__))}
    return np.array([order[w.line] for w in v.windows])


def alike(v: Voices, one: list[int], other: list[int]) -> float:
    return float(v.sims[np.ix_(one, other)].mean())


def exchanges(v: Voices, turns: np.ndarray) -> list[float]:
    """How alike two turns one after the other under two labels are, one number a change of
    hands (a long turn's many windows do not outweigh the rest)."""
    found = []
    for turn in range(int(turns.max())):
        one, other = np.flatnonzero(turns == turn), np.flatnonzero(turns == turn + 1)
        if v.windows[one[0]].label != v.windows[other[0]].label:
            found.append(alike(v, one.tolist(), other.tolist()))
    return found


def calibrated(v: Voices) -> float:
    """How alike two voices must be to join, measured on the clip (JOIN_HIGH with one label):
    windows sharing no sound of one turn (else of one label's turns NEXT apart at most), against
    two turns one after the other under two labels, as the listener heard the talk change hands,
    so a label swapped from some point on does not count as one voice."""
    upper = np.triu(np.ones_like(v.sims, dtype=bool), 1)
    starts = np.array([w.start for w in v.windows])
    turns = turn_of(v)
    labels = np.array([w.label for w in v.windows])
    steps = np.abs(turns[:, None] - turns[None, :])
    own = upper & (np.abs(starts[:, None] - starts[None, :]) >= WINDOW)
    within = v.sims[own & (steps == 0)]
    if not len(within):
        within = v.sims[own & (labels[:, None] == labels[None, :]) & (steps <= NEXT)]
    across = exchanges(v, turns)
    if not len(within) or not across:
        return JOIN_HIGH
    middle = (np.percentile(within, QUARTER) + np.percentile(across, THREE_QUARTERS)) / 2
    return float(np.clip(middle, JOIN_LOW, JOIN_HIGH))


def bound(label: str) -> bool:
    """Whether the label is the listener's own name in a request: not another pass's or a
    request's of its own."""
    return "~p" not in label and not REQUEST.search(label)


def told_apart(v: Voices, ids: np.ndarray) -> Pairs:
    """The voices the listener told apart as it heard them: a window of one said between two of
    the other's NEAR_S apart at most, under another of the listener's own labels."""
    last: dict[int, tuple[float, str]] = {}
    found: Pairs = set()
    for k in sorted(range(len(v.windows)), key=lambda k: v.windows[k].start):
        window, voice = v.windows[k], int(ids[k])
        before = last.get(voice)
        if before is not None and window.start - before[0] <= NEAR_S and bound(window.label):
            found |= {frozenset((voice, other)) for other, (seen, label) in last.items()
                      if other != voice and seen > before[0] and label != window.label
                      and bound(label)}
        last[voice] = (window.start, window.label)
    return found


def needed(one: frozenset[int], other: frozenset[int], apart: Pairs, join: float) -> float:
    told = any(frozenset((a, b)) in apart for a in one for b in other)
    return max(join, APART_JOIN) if told else join


def joined(v: Voices, ids: np.ndarray, join: float) -> np.ndarray:
    """The voices joined: average linkage, most alike first, while alike enough."""
    apart = told_apart(v, ids)
    clusters = [frozenset([k]) for k in sorted(set(ids.tolist()))]
    members = {c: np.flatnonzero(ids == min(c)).tolist() for c in clusters}
    while len(clusters) > 1:
        scored = [(alike(v, members[a], members[b]) - needed(a, b, apart, join), a, b)
                  for k, a in enumerate(clusters) for b in clusters[k + 1:]]
        margin, a, b = max(scored, key=lambda s: s[0])
        if margin < 0:
            break
        clusters = [c for c in clusters if c not in (a, b)] + [a | b]
        members[a | b] = members[a] + members[b]
    place = {k: n for n, c in enumerate(clusters) for k in c}
    return np.array([place[int(k)] for k in ids])


def centres(v: Voices, ids: np.ndarray, count: int) -> np.ndarray:
    sums = np.stack([v.vecs[ids == k].sum(axis=0) for k in range(count)])
    sizes = np.linalg.norm(sums, axis=1, keepdims=True)
    return np.where(sizes > 0, sums / np.where(sizes > 0, sizes, 1.0), 0.0)


def settled(v: Voices, ids: np.ndarray) -> np.ndarray:
    """Each window with the voice it is nearest, again until nothing moves."""
    for _ in range(ROUNDS):
        count = int(ids.max()) + 1
        moved = np.argmax(v.vecs @ centres(v, ids, count).T, axis=1)
        if np.array_equal(moved, ids):
            break
        ids = moved
    return ids


def inner(v: Voices, picked: list[int]) -> float:
    """How alike two of the picked windows are, on average (1.0 for one window)."""
    block = v.sims[np.ix_(picked, picked)]
    pairs = len(picked) * (len(picked) - 1)
    return float((block.sum() - np.trace(block)) / pairs) if pairs else 1.0


def grown(v: Voices, ids: np.ndarray, join: float) -> np.ndarray:
    """The voices with one more for the windows near none, while they are FAR_S or more and
    one voice (alike by join): noisy windows of several voices are no new person."""
    for _ in range(MORE):
        count = int(ids.max()) + 1
        far = np.max(v.vecs @ centres(v, ids, count).T, axis=1) < NEAREST
        if v.seconds[far].sum() < FAR_S or inner(v, np.flatnonzero(far).tolist()) < join:
            break
        ids = settled(v, np.where(far, count, ids))
    return np.unique(ids, return_inverse=True)[1].reshape(-1)


def canonical(ids: np.ndarray) -> list[int]:
    """The voices numbered by their first window, so two ways of numbering compare."""
    first: dict[int, int] = {}
    return [first.setdefault(int(k), len(first)) for k in ids]


def heard_voices(v: Voices, join: float) -> np.ndarray:
    """The voice of each window: the groups joined, each window to its nearest voice, and
    again on the voices that leaves (ROUNDS at most), until they stay."""
    ids = np.unique(np.array(v.groups), return_inverse=True)[1].reshape(-1)
    for _ in range(ROUNDS):
        again = grown(v, settled(v, joined(v, ids, join)), join)
        if canonical(again) == canonical(ids):
            break
        ids = again
    return ids
