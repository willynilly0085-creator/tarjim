"""Whether the voices the windows found can be trusted to move a line (2026-11-09).

Nothing is moved when the voices are not clearly apart: windows on average under SILHOUETTE
nearer their own voice than the next, or the lines' voices as listen/lined.unreliable finds
them (one voice under two labels, voices too alike). Fewer than two voices with ENOUGH_S of
windows each is too little to tell by windows at all; the line check decides then.
"""
from collections import defaultdict

import numpy as np

from tarjim.listen.cluster import FEWEST, Voices
from tarjim.listen.lined import Labels, Prints, unreliable
from tarjim.speakers import Line

SILHOUETTE = 0.15  # windows must be at least this much nearer their own voice, on average
ENOUGH_S = 10.0  # seconds of windows each of two voices needs to be told apart here


def unit(vector: np.ndarray) -> np.ndarray:
    size = float(np.linalg.norm(vector))
    return vector / size if size > 0 else vector


def silhouette(v: Voices, ids: np.ndarray) -> float:
    """How much nearer each window is to its own voice than to the next, on average (cosine)."""
    count = int(ids.max()) + 1
    if count < FEWEST:
        return 0.0
    far = 1.0 - v.sims
    sizes = np.bincount(ids, minlength=count).astype(float)
    totals = np.stack([far[:, ids == k].sum(axis=1) for k in range(count)], axis=1)
    own = sizes[ids] - 1
    inner = np.where(own > 0, totals[np.arange(len(ids)), ids] / np.maximum(own, 1), 0.0)
    means = totals / np.maximum(sizes, 1)
    means[np.arange(len(ids)), ids] = np.inf
    outer = means.min(axis=1)
    found = np.where(own > 0, (outer - inner) / np.maximum(np.maximum(outer, inner), 1e-9), 0.0)
    return float(found.mean())


def doubt(v: Voices, ids: np.ndarray, labels: Labels) -> str:
    """Why the voices found cannot be trusted, or "" when they can."""
    quality = silhouette(v, ids)
    if quality < SILHOUETTE:
        return f"the voices are not clearly apart (silhouette {quality:.2f}, under {SILHOUETTE})"
    by_line: dict[Line, list[int]] = defaultdict(list)
    for k, window in enumerate(v.windows):
        by_line[window.line].append(k)
    voices_of = {line: unit(v.vecs[picked].sum(axis=0)) for line, picked in by_line.items()}
    return unreliable(Prints(voices_of, frozenset(voices_of)), {
        line: labels[line] for line in voices_of})


def enough(v: Voices, ids: np.ndarray) -> bool:
    seconds = np.bincount(ids, weights=v.seconds)
    return int((seconds >= ENOUGH_S).sum()) >= FEWEST
