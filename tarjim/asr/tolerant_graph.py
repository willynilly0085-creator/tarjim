"""The states the tolerant reading (asr/tolerant.py) walks through, and the moves between them
(2026-11-08).

Each letter of the text has its state with a blank before it, as in the strict reading
(asr/ctc.py). With a star, each blank between two words and at both ends gets a star beside it,
entered at costs.star_enter (paid once), left back to its blank or to the next word's first
letter. With `skip`, the blank before each word has a step to the blank after it, priced by the
word's letters (costs.Costs.skip_cost). Each move is one of five codes, so a frame's move into a
state fits in a byte.
"""
from dataclasses import dataclass, field
from itertools import groupby

import numpy as np
from numpy.typing import NDArray

from tarjim.asr.costs import Costs
from tarjim.asr.ctc import BLANK, Bounds

STAY, STEP, HOP, WORD, STAR = range(5)  # stay; from the state before; over a blank; a word; star


@dataclass(frozen=True)
class Text:
    """The letters to find, the word each belongs to (in order) and each letter's window."""
    tokens: list[int]
    word_of: list[int]
    bounds: Bounds | None = None

    @property
    def words(self) -> int:
        return max(self.word_of, default=-1) + 1


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
