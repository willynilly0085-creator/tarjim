"""The coverage check again, after alignment: speech that no timed word reaches.

The check on lines (listen/coverage.py) trusts a line's span. A cloud listener often returns one
long line stretched over a sentence it never wrote (2026-10-31: a Rubio clip lost "As diplomats,
as political leaders, we have a vital role to play" inside a 55-71 s line; an 832 s interview
lost 4 s inside an 80 s line), and the aligner can pile a line's words onto one instant (a
Persian clip, 78-89 s). Here speech counts as covered only near a timed word. Piled words are
spread back over their stretch (asr/piles.py); text left out is heard again by the same engine,
deduplicated by its words and by the timed words, not by line spans; then the local words fill.
"""
from dataclasses import dataclass, replace

from tarjim.asr.piles import Span, piles, spread
from tarjim.listen.coverage import EDGE, Gap, Hearing, gaps, speech_of
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.novel import Again, WordMender
from tarjim.listen.repair import described
from tarjim.listen.timing import Timer
from tarjim.models import Word

INF = float("inf")
NARROWEST = 0.5  # seconds: a stretch this short has no room to spread words over


@dataclass(frozen=True)
class Checked:
    utterances: list[Utterance]
    words: list[Word]
    added: list[Utterance]
    left: list[Gap]


def touches(span: Span, gap: Gap) -> bool:
    return span[0] < gap.end and span[1] > gap.start


def word_gaps(hearing: Hearing, words: list[Word], tried: list[Gap]) -> list[Gap]:
    lines = [Utterance(w.start, w.end, w.speaker, w.text) for w in words]
    found = gaps(Hearing(lines, hearing.local, hearing.regions))
    return [g for g in found if not any(touches((t.start, t.end), g) for t in tried)]


def bounds(words: list[Word], first: int, past: int) -> Span:
    """Between the words around a pile."""
    return (words[first - 1].end if first else 0.0,
            words[past].start if past < len(words) else INF)


def room(words: list[Word], run: tuple[int, int], gap: Gap) -> Span:
    """The gap and the pile together, never past the words around them."""
    (first, past), (before, after) = run, bounds(words, *run)
    return (max(before, min(gap.start, words[first].start)),
            min(after, max(gap.end, words[past - 1].end)))


def realigned(pile: list[Word], span: Span, timer: Timer) -> list[Word] | None:
    line = Utterance(span[0], span[1], pile[0].speaker, " ".join(w.text for w in pile))
    again = timer.part([line])
    fits = all(span[0] - EDGE <= w.start and w.end <= span[1] + EDGE for w in again)
    if len(again) != len(pile) or piles(again) or not fits:
        return None
    return [replace(w, start=a.start, end=a.end) for w, a in zip(pile, again, strict=True)]


def unpiled(words: list[Word], found: list[Gap], speech: list[Span], timer: Timer) -> list[Word]:
    words = list(words)
    for first, past in piles(words):
        gap = next((g for g in found if touches(bounds(words, first, past), g)), None)
        span = room(words, (first, past), gap) if gap else (0.0, 0.0)
        if gap is None or span[1] - span[0] < NARROWEST:
            continue
        pile = words[first:past]
        words[first:past] = realigned(pile, span, timer) or spread(pile, span, speech)
        print(f"coverage: words {described(gap)} -> timing collapsed: re-timed {len(pile)} "
              f"words into {span[0]:.1f}-{span[1]:.1f} s", flush=True)
    return words


def joined(words: list[Word], lines: list[Utterance], timer: Timer) -> list[Word]:
    """Each added line's words go in at their own time, as one piece (asr/fuse.slotted)."""
    from tarjim.asr.fuse import slotted, split_by

    return slotted(words, split_by(timer.part(lines), lines))


def recheck(hearing: Hearing, words: list[Word], timer: Timer, again: Again) -> Checked:
    found = word_gaps(hearing, words, again.tried)
    if not found:
        return Checked(hearing.utterances, words, [], [])
    words = unpiled(words, found, speech_of(hearing), timer)
    missing = word_gaps(hearing, words, again.tried)
    mended = WordMender(hearing, again, words).mend(missing)
    if mended.added:
        words = joined(words, sorted(mended.added, key=lambda u: u.start), timer)
    return Checked(mended.utterances, words, mended.added, mended.left)
