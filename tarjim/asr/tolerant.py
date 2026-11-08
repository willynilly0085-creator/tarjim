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

Each frame's move into each state is one byte (STAY, STEP, HOP, WORD, STAR), read back through a
table of where each move comes from, so a 70-letter word stepped over needs no wide numbers and
the memory stays frames x states bytes. The strict reading stays the only check of what is said
where (agree.run_score); nothing here times words yet.
"""
from dataclasses import dataclass, field
from itertools import groupby

import numpy as np
from numpy.typing import NDArray

from tarjim.asr.costs import Costs
from tarjim.asr.ctc import BLANK, FRAME, NEG, OUTSIDE_PENALTY, Bounds, Span, span_of

STAY, STEP, HOP, WORD, STAR = range(5)  # stay; from the state before; over a blank; a word; star
ABSORBED = 15  # frames: a star stretch of 0.3 s or more is told


@dataclass(frozen=True)
class Text:
    """The letters to find, the word each belongs to (in order) and each letter's window."""
    tokens: list[int]
    word_of: list[int]
    bounds: Bounds | None = None

    @property
    def words(self) -> int:
        return max(self.word_of, default=-1) + 1


@dataclass(frozen=True)
class Placed:
    """Each letter's span (None where its word was left out), whether each word was placed,
    and the stretches of 0.3 s or more the star took, in seconds."""
    spans: list[Span | None]
    placed: list[bool]
    absorbed: list[tuple[float, float]]


@dataclass
class Graph:
    """The states (their letter, the star being one past the last), where each move into each
    comes from and what it costs, and where a reading may start and end."""
    labels: list[int] = field(default_factory=list)
    token: list[int] = field(default_factory=list)  # the letter's index in the text, else -1
    arcs: list[tuple[int, int, int, float]] = field(default_factory=list)  # move, to, from, cost
    starts: list[tuple[int, float]] = field(default_factory=list)
    ends: list[int] = field(default_factory=list)
    star: int = -1  # the star's label: the column after the letters

    def tables(self) -> tuple[NDArray[np.intp], NDArray[np.float64]]:
        """Per move and state, the state it comes from (one past the last for none) and its
        cost."""
        states = len(self.labels)
        source = np.full((5, states), states, dtype=np.intp)
        cost = np.zeros((5, states))
        for move, to, came, price in self.arcs:
            source[move, to], cost[move, to] = came, price
        return source, cost


class Builder:
    def __init__(self, text: Text, costs: Costs | None, star: int) -> None:
        self.text, self.costs = text, costs
        self.graph = Graph(star=star)
        self.letter = -1  # the last letter's state

    def add(self, label: int, token: int = -1) -> int:
        state = len(self.graph.labels)
        self.graph.labels.append(label)
        self.graph.token.append(token)
        self.graph.arcs.append((STAY, state, state, 0.0))
        return state

    def boundary(self) -> tuple[int, int]:
        """The blank between two words (or at an end) and its star; -1 with the star off."""
        blank = self.add(BLANK)
        if self.letter >= 0:
            self.graph.arcs.append((STEP, blank, self.letter, 0.0))
        if self.costs is None or not self.costs.star:
            return blank, -1
        star, enter = self.add(self.graph.star), self.costs.star_enter
        self.graph.arcs += [(STEP, star, blank, enter), (STAR, blank, star, 0.0)]
        if self.letter >= 0:
            self.graph.arcs.append((HOP, star, self.letter, enter))
        return blank, star

    def word(self, first: int, past: int, blank: int, star: int) -> None:
        tokens = self.text.tokens
        for k in range(first, past):
            before = blank if k == first else self.add(BLANK)
            if k > first:
                self.graph.arcs.append((STEP, before, self.letter, 0.0))
            letter = self.add(tokens[k], k)
            self.graph.arcs.append((STEP, letter, before, 0.0))
            if k and tokens[k] != tokens[k - 1]:
                self.graph.arcs.append((HOP, letter, self.letter, 0.0))
            if k == first and star >= 0:
                self.graph.arcs.append((STAR, letter, star, 0.0))
            self.letter = letter

    def built(self) -> Graph:
        blank, star = self.boundary()
        enter = self.costs.star_enter if self.costs else 0.0
        starts = [(blank, 0.0), (star, enter)]
        for _, letters in groupby(range(len(self.text.tokens)), key=self.text.word_of.__getitem__):
            span = list(letters)
            self.word(span[0], span[-1] + 1, blank, star)
            before, (blank, star) = blank, self.boundary()
            if self.costs is not None and self.costs.skipping:
                self.graph.arcs.append((WORD, blank, before, self.costs.skip_cost(len(span))))
        self.graph.ends = [blank, self.letter, star]
        starts.insert(1, (self.graph.token.index(0), 0.0))
        self.graph.starts = [(s, c) for s, c in starts if s >= 0]
        self.graph.ends = [s for s in self.graph.ends if s >= 0]
        return self.graph


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
