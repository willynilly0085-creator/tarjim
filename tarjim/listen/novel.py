"""Whether a line heard again after alignment is new speech. The line check (listen/repair.py)
drops a line that overlaps an earlier line's span; inside a stretched line that drops exactly the
sentence that was left out. Here a line is old when its words were said nearby (pairs of words in
order, so common words alone do not match) or when timed words already fill most of its time."""
from dataclasses import dataclass
from itertools import pairwise

from tarjim.listen.coverage import Gap, Hearing, merged, outside
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.repair import NEAR, OVERLAP, REPEATED, Mender, Relisten, from_words
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words


@dataclass(frozen=True)
class Again:
    relisten: Relisten | None
    name: str
    tried: list[Gap]  # left by the check on lines: asked about already


def said(text: str) -> list[str]:
    return [norm(w) for w in split_words(text) if norm(w)]


def grams(words: list[str]) -> set[tuple[str, ...]]:
    """Pairs of words in order; a one-word line is its word."""
    return set(pairwise(words)) if len(words) > 1 else {(w,) for w in words}


def said_before(line: Utterance, lines: list[Utterance]) -> bool:
    mine = grams(said(line.text))
    near: set[tuple[str, ...]] = set()
    for other in lines:
        if other.start - NEAR <= line.end and line.start <= other.end + NEAR:
            theirs = said(other.text)
            near |= grams(theirs) | {(w,) for w in theirs}
    return bool(mine) and len(mine & near) >= REPEATED * len(mine)


def timed_over(line: Utterance, spans: list[tuple[float, float]]) -> bool:
    length = max(line.end - line.start, 0.01)
    free = sum(b - a for a, b in outside((line.start, line.end), spans))
    return length - free > OVERLAP * length


class WordMender(Mender):
    label = "words "

    def __init__(self, hearing: Hearing, again: Again, words: list[Word]) -> None:
        super().__init__(hearing, again.relisten, again.name)
        self.spans = merged([(w.start, w.end) for w in words], 0.0)

    def novel(self, line: Utterance, lines: list[Utterance]) -> bool:
        return not said_before(line, lines) and not timed_over(line, self.spans)

    def from_local(self, gap: Gap, lines: list[Utterance]) -> list[Utterance]:
        return [u for u in from_words(gap.words) if not said_before(u, lines)]
