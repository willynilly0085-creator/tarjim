"""Words the aligner piled onto one instant, and how they are spread back over their speech.

On a Persian clip (2026-10-31) the cloud listener's line 77.8-95.8 s held every word, but the
forced aligner put about 35 of them at 90.1 s: the subtitles for 78-89 s were missing, then all
flashed at once. Over the whole clip the timing looked sane (asr/sanity.py), so only a local look
finds it: several words in a row ending within a few hundredths of a second of each other.
"""
from dataclasses import replace

from tarjim.asr.align import longest
from tarjim.models import Word

STEP = 0.08  # seconds between two words' ends: closer than anyone speaks
PILE = 5  # this many words that close in a row were piled, not said

Span = tuple[float, float]


def piles(words: list[Word]) -> list[tuple[int, int]]:
    """Each run of piled words, as (first, past)."""
    found, first = [], 0
    for index in range(1, len(words) + 1):
        if index < len(words) and abs(words[index].end - words[index - 1].end) < STEP:
            continue
        if index - first >= PILE:
            found.append((first, index))
        first = index
    return found


def at(pieces: list[Span], offset: float) -> float:
    """The moment `offset` seconds of speech into the pieces."""
    for low, high in pieces:
        if offset <= high - low:
            return low + offset
        offset -= high - low
    return pieces[-1][1]


def spread(pile: list[Word], span: Span, speech: list[Span]) -> list[Word]:
    """The piled words share the speech inside the span, each by its length, in order; with no
    speech known there, the whole span."""
    pieces = [(max(a, span[0]), min(b, span[1])) for a, b in speech]
    pieces = [p for p in pieces if p[1] > p[0]] or [span]
    weights = [longest(w.text) for w in pile]
    step = sum(b - a for a, b in pieces) / sum(weights)
    words, cursor = [], 0.0
    for word, weight in zip(pile, weights, strict=True):
        end = cursor + weight * step
        words.append(replace(word, start=at(pieces, cursor), end=at(pieces, end)))
        cursor = end
    return words
