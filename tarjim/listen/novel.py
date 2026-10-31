"""Whether a line heard again after alignment is new speech. The line check (listen/repair.py)
drops a line that overlaps an earlier line's span; inside a stretched line that drops exactly the
sentence that was left out. Here a line is old when its words were said nearby (pairs of words in
order, so common words alone do not match) or when timed words already fill most of its time.
A line of a word or two is old when its words echo timed words close by: a listener asked about a
stretch next to a word often hears a piece of that word again ("بگوئه." after "گفت‌وگوئه.")."""
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import pairwise

from tarjim.listen.coverage import Gap, Hearing, merged, outside
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.repair import NEAR, OVERLAP, REPEATED, Mender, Relisten, from_words
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

SHORT = 2  # words: a line this short has no pairs worth comparing
SHORTEST = 3  # letters: a shorter word echoes only by being the same word
ECHO = 0.75  # share of the shorter word's letters, in one piece, that the other word holds
# Letters written more than one way (Arabic and Persian forms, hamza seats); the half-space and
# punctuation go in norm.
FOLD = str.maketrans("يىكةأإآؤئۀ", "ییکهاااویه")


@dataclass(frozen=True)
class Again:
    relisten: Relisten | None
    name: str
    tried: list[Gap]  # left by the check on lines: asked about already


def said(text: str) -> list[str]:
    return [norm(w).translate(FOLD) for w in split_words(text) if norm(w)]


def alike(one: str, other: str) -> bool:
    """The same word, or one holding most of the other in one piece."""
    short, long = sorted((one, other), key=len)
    match = SequenceMatcher(None, short, long, autojunk=False).find_longest_match()
    return short == long or (len(short) >= SHORTEST and match.size >= ECHO * len(short))


def echoes(line: Utterance, words: list[Word]) -> bool:
    mine = said(line.text)
    near = [t for w in words if w.start - NEAR <= line.end and line.start <= w.end + NEAR
            for t in said(w.text)]
    same = sum(any(alike(word, other) for other in near) for word in mine)
    return bool(mine) and len(mine) <= SHORT and same >= REPEATED * len(mine)


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
        self.words, self.spans = words, merged([(w.start, w.end) for w in words], 0.0)

    def novel(self, line: Utterance, lines: list[Utterance]) -> bool:
        return not (said_before(line, lines) or timed_over(line, self.spans)
                    or echoes(line, self.words))

    def from_local(self, gap: Gap, lines: list[Utterance]) -> list[Utterance]:
        return [u for u in from_words(gap.words) if not said_before(u, lines)]
