"""The end of the piece before, heard again by each piece's request (2026-11-09).

Every piece of a long clip is a request of its own, and a listener names its speakers in the order
it hears them: piece two's "S1" may be piece one's "S2", and nothing linked them, so one person
took the other's colour and voice from a cut on. So each request after the first also hears the
last LINK_LEAD seconds of the piece before it, WIDE_LEAD when the voice detector found little
speech there, never more than LEAD_SHARE of a piece: about 9% more sound and no request more.
The pause cut still decides which piece a line is in. The lead's lines only tell who is who
(listen/links.py) and are never shown; a line heard over the cut keeps the words the piece
before does not hold (owned).
"""
from dataclasses import replace
from difflib import SequenceMatcher

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, Piece
from tarjim.listen.vote import SIMILAR, norm
from tarjim.scripts import joined, split_words

LINK_LEAD = 7.0  # seconds of the piece before that a request hears too
WIDE_LEAD = 12.0  # ...when that stretch holds little speech
LEAD_SPEECH = 1.5  # seconds of speech in LINK_LEAD that is little
LEAD_SHARE = 0.16  # the most a request hears beyond its piece, as a share of a piece
SLACK = 1  # words the piece before may have heard of a line past where the lead's matched it

Span = tuple[float, float]
Run = list[Utterance]


def speech_in(regions: list[Span], low: float, high: float) -> float:
    return sum(max(0.0, min(b, high) - max(a, low)) for a, b in regions)


def lead_of(spans: list[Span], k: int, regions: list[Span], size: float) -> float:
    """The seconds before piece k that its request hears too; none for the first. With no voice
    detector's regions there is nothing to judge the speech by, and LINK_LEAD stands."""
    if k == 0:
        return 0.0
    start = spans[k][0]
    little = bool(regions) and speech_in(regions, start - LINK_LEAD, start) < LEAD_SPEECH
    return min(WIDE_LEAD if little else LINK_LEAD, LEAD_SHARE * size, start - spans[k - 1][0])


def middle(u: Utterance) -> float:
    return (u.start + u.end) / 2


def keys(u: Utterance) -> list[str]:
    return [norm(w) or w for w in split_words(u.text)]


def overlap(mine: list[str], other: list[str]) -> int:
    """How many of a line's first words `other` ends with, or holds all of: the piece before was
    heard up to its cut, so its line over the cut ends where the lead's goes on."""
    blocks = [b for b in SequenceMatcher(None, mine, other, autojunk=False).get_matching_blocks()
              if b.size]
    if not blocks:
        return 0
    last = blocks[-1]
    held = last.a + last.size
    reaches = held == len(mine) or last.b + last.size >= len(other) - SLACK
    return held if reaches and sum(b.size for b in blocks) >= SIMILAR * held else 0


def held(u: Utterance, before: Run) -> int:
    """The first words of a line heard over the cut that a line of the piece before holds."""
    mine = keys(u)
    return max((overlap(mine, keys(o)) for o in before if o.end > u.start), default=0)


def owned(u: Utterance, lead_s: float, length: float, before: Run) -> Utterance | None:
    """A line of the piece at the piece's own times. One heard over the cut keeps the words the
    piece before does not hold, from about where they were said and never before the cut, with a
    wall back over the lead; with none left it is dropped (2026-11-09: one said mostly before the
    cut was the lead's and its last words were lost, one said mostly after was kept whole and its
    first words were shown twice)."""
    if u.start >= lead_s:
        return replace(u, start=u.start - lead_s, end=u.end - lead_s)
    words, n = split_words(u.text), held(u, before)
    if guards.when("lead.over_cut", n >= len(words)):
        return None
    start = max(u.start + n / len(words) * (u.end - u.start), lead_s) - lead_s
    return replace(u, start=start, end=max(start, u.end - lead_s), piece=(-lead_s, length),
                   text=joined(words[n:]) if n else u.text)


def split(run: Run, lead_s: float, length: float, before: Run) -> tuple[Run, Run]:
    """A pass heard from lead_s before its piece, `length` long: its piece's lines at the piece's
    times, and the lead's as heard. Its lines are placed first at the request's own times, the
    ones its listener wrote: an mm:ss misread is read back there (2026-11-09: read back after the
    lead was taken off, 1:03 written 103 in a 7 s lead became 96 and no time at all)."""
    if lead_s <= 0:
        return run, []
    from tarjim.listen.chunks import placed_in

    run = placed_in(run, lead_s + length)
    lead = [u for u in run if middle(u) < lead_s]
    own = [line for u in run if u.end > lead_s and (line := owned(u, lead_s, length, before))]
    return own, lead


def tail(piece: Piece, origin: float) -> Run:
    """The piece's lines of every pass that end after `origin`, at times from there."""
    return [replace(u, start=u.start + piece.start - origin, end=u.end + piece.start - origin)
            for run in piece.passes for u in run if u.end + piece.start > origin]


def pieces_of(spans: list[Span], heard: list[tuple[float, Heard]]) -> list[Piece]:
    """Each piece as heard with its lead: its passes at its own times and the lead's lines."""
    pieces: list[Piece] = []
    for (start, end), (lead_s, one) in zip(spans, heard, strict=True):
        before = tail(pieces[-1], start - lead_s) if pieces else []
        runs = [split(run, lead_s, end - start, before) for run in one.passes]
        lead = [lines for _, lines in runs] if lead_s > 0 else []
        pieces.append(Piece(start, end, [own for own, _ in runs], one.language, lead_s, lead))
    return pieces
