"""The aligner's letters read with room for a text that is not quite what was said (2026-11-08).

The strict reading (asr/ctc.py) must give every letter of the text a frame and every frame to a
letter or a blank, so a stretch the text does not hold (a line nobody wrote down) drags the words
beside it over it, and a word that is not said is squeezed in somewhere. This reading adds:

- a star beside each blank between two words and at both ends: it takes any sound at
  max(blank, loudest letter - delta) a frame, entered at a price paid once, and can go back to
  its blank; with the text exactly as said it is never worth taking, so the reading is the
  strict one;
- with `skip`, a step from the blank before a word to the blank after it, priced by the word's
  letters (costs.Costs.skip_cost), so a word the sound does not hold is left out.

Each frame's move into each state is one byte (the codes of asr/tolerant_graph.py), read back
through a table of where each move comes from, so a 70-letter word stepped over needs no wide
numbers and the memory stays frames x states bytes. The strict reading stays the only check of
what is said where (agree.run_score); nothing here times words yet.
"""
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tarjim.asr.costs import Costs
from tarjim.asr.ctc import BLANK, FRAME, NEG, OUTSIDE_PENALTY, Bounds, Span, span_of
from tarjim.asr.tolerant_graph import Builder, Graph, Text

__all__ = ["Decoded", "Placed", "Text", "decoded", "tolerant_spans"]
ABSORBED = 15  # frames: a star stretch of 0.3 s or more is told


@dataclass(frozen=True)
class Placed:
    """Each letter's span (None where its word was left out), whether each word was placed,
    and the stretches of 0.3 s or more the star took, in seconds."""
    spans: list[Span | None]
    placed: list[bool]
    absorbed: list[tuple[float, float]]


def with_star(logp: NDArray[np.floating], delta: float, hard: NDArray[np.bool_] | None,
              ) -> NDArray[np.floating]:
    """The letters with the star's column after them: max(blank, loudest letter - delta), and
    never on a `hard` frame (silence for sure)."""
    star = np.maximum(logp[:, BLANK], np.delete(logp, BLANK, axis=1).max(axis=1) - delta)
    if hard is not None:
        star = np.where(hard[:len(logp)], NEG, star)
    return np.concatenate([logp, star[:, None].astype(logp.dtype)], axis=1)


@dataclass
class Decoded:
    graph: Graph
    back: NDArray[np.int8]
    path: NDArray[np.intp] | None  # None: the text cannot be read in this sound

    def on_star(self) -> NDArray[np.bool_]:
        stars = np.asarray(self.graph.labels) == self.graph.star
        return np.zeros(len(self.back), bool) if self.path is None else stars[self.path]


def windows(graph: Graph, text: Text, frames: int) -> Bounds:
    low = np.zeros(len(graph.labels), dtype=np.int64)
    high = np.full(len(graph.labels), frames, dtype=np.int64)
    if text.bounds is not None:
        letters = np.flatnonzero(np.asarray(graph.token) >= 0)
        low[letters], high[letters] = text.bounds
    return low, high


def forward(sound: NDArray[np.floating], graph: Graph, window: Bounds,
            ) -> tuple[NDArray[np.int8], NDArray[np.float64]]:
    """Each frame's best move into each state, and the last frame's scores (as ctc.viterbi)."""
    labels, (low, high) = np.asarray(graph.labels), window
    source, cost = graph.tables()
    scores = np.full(len(labels) + 1, NEG)
    first = sound[0, labels] - OUTSIDE_PENALTY * ((low > 0) | (high <= 0))
    for state, price in graph.starts:
        scores[state] = first[state] - price
    back = np.zeros((len(sound), len(labels)), dtype=np.int8)
    for t in range(1, len(sound)):
        candidates = scores[source] - cost
        back[t] = candidates.argmax(axis=0)
        # the letters' own score first, then added, in ctc.emission's order to the last bit
        scores[:-1] = candidates.max(axis=0) + (
            sound[t, labels] - OUTSIDE_PENALTY * ((t < low) | (t >= high)))
    return back, scores[:-1]


def decoded(logp: NDArray[np.floating], text: Text, costs: Costs | None,
            hard: NDArray[np.bool_] | None = None) -> Decoded:
    star = costs.star_delta if costs is not None else None
    graph = Builder(text, costs, logp.shape[1]).built()
    sound = logp if star is None else with_star(logp, star, hard)
    back, scores = forward(sound, graph, windows(graph, text, len(logp)))
    end = graph.ends[int(np.argmax(scores[graph.ends]))]
    if scores[end] < NEG / 2:
        return Decoded(graph, back, None)
    source, _ = graph.tables()
    path = np.empty(len(logp), dtype=np.intp)
    for t in range(len(logp) - 1, -1, -1):
        path[t], end = end, source[back[t, end], end]
    return Decoded(graph, back, path)


def tolerant_spans(logp: NDArray[np.floating], text: Text, costs: Costs | None,
                   hard: NDArray[np.bool_] | None = None) -> Placed:
    """Each letter's span, read with the star and the skip `costs` allow; with costs None (or
    no star) exactly ctc.token_spans, a text that cannot be read giving no spans at all."""
    if not text.tokens:
        return Placed([], [False] * text.words, [])
    found = decoded(logp, text, costs, hard)
    frames: list[list[int]] = [[] for _ in text.tokens]
    for t, state in enumerate([] if found.path is None else found.path):
        if found.graph.token[state] >= 0:
            frames[found.graph.token[state]].append(t)
    spans = [span_of(logp, f, text.tokens[k]) if f else None for k, f in enumerate(frames)]
    missing = {text.word_of[k] for k, span in enumerate(spans) if span is None}
    placed = [w in text.word_of and w not in missing for w in range(text.words)]
    return Placed(spans, placed, absorbed(found.on_star()))


def absorbed(on_star: NDArray[np.bool_]) -> list[tuple[float, float]]:
    edges = np.flatnonzero(np.diff(np.concatenate([[0], on_star.astype(np.int8), [0]])))
    return [(a * FRAME, b * FRAME) for a, b in zip(edges[::2], edges[1::2], strict=True)
            if b - a >= ABSORBED]
