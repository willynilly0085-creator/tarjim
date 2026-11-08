"""The end of the piece before, heard again by each piece's request (2026-11-09).

Every piece of a long clip is a request of its own, and a listener names its speakers in the order
it hears them: piece two's "S1" may be piece one's "S2", and nothing linked them, so one person
took the other's colour and voice from a cut on. So each request after the first also hears the
last LINK_LEAD seconds of the piece before it, WIDE_LEAD when the voice detector found little
speech there, never more than LEAD_SHARE of a piece: about 9% more sound and no request more.
The pause cut still decides which piece a line is in. The lead's lines only tell who is who
(listen/links.py) and are never shown; a line heard over the cut is dropped when the piece before
holds its words, else it starts at the cut.
"""
from dataclasses import replace

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, Piece

LINK_LEAD = 7.0  # seconds of the piece before that a request hears too
WIDE_LEAD = 12.0  # ...when that stretch holds little speech
LEAD_SPEECH = 1.5  # seconds of speech in LINK_LEAD that is little
LEAD_SHARE = 0.16  # the most a request hears beyond its piece, as a share of a piece

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


def owned(u: Utterance, lead_s: float, before: Run) -> Utterance | None:
    """A line of the piece at the piece's own times. One heard over the cut is dropped when the
    piece before holds its words, else it starts at the cut."""
    from tarjim.listen.chunks import novel

    if u.start < lead_s and guards.when("lead.over_cut", not novel(u, before)):
        return None
    start = max(u.start, lead_s) - lead_s
    return replace(u, start=start, end=max(start, u.end - lead_s))


def split(run: Run, lead_s: float, before: Run) -> tuple[Run, Run]:
    """A pass heard from lead_s before its piece: its piece's lines, at the piece's times, and
    the lead's, as heard."""
    if lead_s <= 0:
        return run, []
    lead = [u for u in run if middle(u) < lead_s]
    own = [line for u in run if middle(u) >= lead_s and (line := owned(u, lead_s, before))]
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
        runs = [split(run, lead_s, before) for run in one.passes]
        lead = [lines for _, lines in runs] if lead_s > 0 else []
        pieces.append(Piece(start, end, [own for own, _ in runs], one.language, lead_s, lead))
    return pieces
