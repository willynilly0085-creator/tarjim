"""Long sound is heard in pieces of about 75 seconds, each cut in a pause.

A cloud listener given minutes of sound in one request drifts and leaves speech out: on
2026-10-31 all three passes over a 250-second clip stopped at 178 s and stretched their times to
fill the rest. Short pieces keep every listener close to the sound. Since 2026-11-09 each request
also hears the end of the piece before it (listen/lead.py), and the labels of neighbouring pieces
are linked from what both heard there (listen/links.py): one person, one speaker.
"""
from collections.abc import Callable
from dataclasses import replace
from itertools import pairwise

from tarjim import guards
from tarjim.job import checkpoint
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.lead import lead_of, pieces_of
from tarjim.listen.links import named
from tarjim.listen.merge import Heard, Piece, agreed
from tarjim.listen.minutes import OVERRUN, SLIPPED, ended, read_back, room, unslipped
from tarjim.listen.sized import CHUNK_SECONDS, TAIL_SHARE, chunk_seconds, is_long
from tarjim.listen.vote import SIMILAR, norm
from tarjim.scripts import split_words

SEARCH_SHARE = 0.2  # a cut is looked for this share of a piece either side of its target
LONGEST_SEARCH = 30.0
SHORTEST = 0.3  # seconds a line kept at its piece's edge lasts at the least
CLAMPED = 0.0  # how far the time of a line kept at its piece's edge is trusted: not at all

Span = tuple[float, float]
ListenSpan = Callable[[float, float], Heard]
# moved to listen/sized.py (2026-11-09) and listen/minutes.py (2026-11-14), still offered here
__all__ = ["CHUNK_SECONDS", "OVERRUN", "SLIPPED", "TAIL_SHARE", "chunk_seconds", "is_long"]


def boundary(target: float, regions: list[Span], reach: float) -> float:
    """The longest pause near the target: a sentence ends there more often than at a breath."""
    pauses = [(b[0] - a[1], (a[1] + b[0]) / 2) for a, b in pairwise(regions) if b[0] > a[1]]
    near = [(length, -abs(middle - target), middle) for length, middle in pauses
            if abs(middle - target) <= reach]
    return max(near)[2] if near else target


def spans(duration: float, regions: list[Span], target: float | None = None) -> list[Span]:
    size = chunk_seconds() if target is None else target
    if not is_long(duration, size):
        return [(0.0, duration)]
    reach = min(LONGEST_SEARCH, size * SEARCH_SHARE)
    cuts, aim = [], size
    while aim < duration - size * TAIL_SHARE:
        cut = boundary(aim, regions, reach)
        cuts.append(cut)
        aim = cut + size
    return list(pairwise([0.0, *cuts, duration]))


def novel(u: Utterance, lines: list[Utterance]) -> bool:
    """Its words are not mostly those of one line the piece already has."""
    mine = {norm(w) for w in split_words(u.text)} - {""}
    return bool(mine) and not any(
        len(mine & {norm(w) for w in split_words(o.text)}) >= SIMILAR * len(mine) for o in lines)


def placed_line(u: Utterance, length: float, free: Span,
                others: list[Utterance]) -> Utterance | None:
    """The line at the piece's own times, inside the piece and OVERRUN either side. A line put
    past it is read back from an mm:ss misread, else kept at the edge with no trust in its time
    when no line of the piece says it, else dropped as the listener's invention (2026-11-08:
    every such line was dropped, and a whole line was lost to one mm:ss slip)."""
    high = length + OVERRUN
    if u.start < high:
        start = max(u.start, -OVERRUN)
        return replace(u, start=start, end=max(start, ended(u, high)))
    fixed = unslipped(u, length, free)
    if guards.when("shift.slipped", fixed is not None):
        return fixed
    if not guards.when("shift.clamped", novel(u, others)):
        guards.fired("shift.hallucinated")
        return None
    start = high - SHORTEST
    return replace(u, start=start, end=max(start + SHORTEST, min(u.end, high)), prior=CLAMPED)


def placed_in(utterances: list[Utterance], length: float) -> list[Utterance]:
    """The lines of a request `length` seconds long at its own times (placed_line), in order;
    a pass written in minutes and seconds is read back whole first (listen/minutes.py)."""
    utterances = read_back(utterances, length)
    inside = [u for u in utterances if u.start < length + OVERRUN]
    placed: list[Utterance] = []
    for k, u in enumerate(utterances):
        free = room(placed, utterances[k + 1:], length)
        if (line := placed_line(u, length, free, [*inside, *placed])) is not None:
            placed.append(line)
    return placed


def walled(u: Utterance, span: Span) -> Span:
    """The piece, or the wall of a line heard over its cut (listen/lead.owned, 2026-11-09)."""
    return span if u.piece is None else (span[0] + u.piece[0], span[0] + u.piece[1])


def shift(utterances: list[Utterance], span: Span, tag: str = "",
          request: str = "") -> list[Utterance]:
    """A piece's lines at clip times, each with its piece and the request that heard it."""
    return [replace(u, start=u.start + span[0], end=u.end + span[0], speaker=f"{tag}{u.speaker}",
                    piece=walled(u, span), request=request)
            for u in placed_in(utterances, span[1] - span[0])]


def placeable(lines: list[Utterance]) -> list[Utterance]:
    """The lines whose time can be searched. One kept at its piece's edge (CLAMPED) says nothing
    of where it was said, and the aligner searches only near the time it is given: its words were
    shown where no one said them (2026-11-08). It stays in the hearing, counted and told."""
    kept = [u for u in lines if u.prior > CLAMPED]
    guards.fired("shift.held", len(lines) - len(kept))
    if len(kept) < len(lines):
        print(f"listening: {len(lines) - len(kept)} line(s) heard past their piece's end are "
              "not timed: when they were said is not known", flush=True)
    return kept


def listen_one(span: Span, listen_span: ListenSpan) -> Heard:
    """Each chunk is a step of its own: the person's pause or cancel takes effect before it. Its
    passes are voted again in `joined`, which counts the vote (guards.quiet, 2026-11-08)."""
    checkpoint()
    with guards.quiet():
        return listen_span(*span)


def listen_in_chunks(duration: float, regions: list[Span], listen_span: ListenSpan,
                     target: float | None = None) -> Heard:
    """Each piece heard on its own; one after the first from a little before it (2026-11-09)."""
    cut = spans(duration, regions, target)
    size = chunk_seconds() if target is None else target
    heard = []
    for k, (start, end) in enumerate(cut):
        lead_s = lead_of(cut, k, regions, size)
        heard.append((lead_s, listen_one((start - lead_s, end), listen_span)))
    pieces = pieces_of(cut, heard)
    if len(pieces) > 1:
        print(f"listening: {len(pieces)} pieces, cut in pauses", flush=True)
    utterances, passes = joined(pieces)
    return Heard(heard[0][1].language, utterances, passes, pieces=pieces)


def joined(pieces: list[Piece]) -> tuple[list[Utterance], list[list[Utterance]]]:
    """The clip's lines, each piece's passes voted on their own (merge.agreed), and its passes,
    pass n being every piece's n-th pass. Each line names its request (2026-11-08): "k0.v" the
    vote of piece 0, "k0.p1" its pass 1. The same for a fresh hearing and a kept one, so a kept
    hearing is voted again exactly as it was heard (2026-11-08: the joined passes were voted, and
    one broken line in one piece cost a reply in another). Each piece's speakers are named as the
    clip's (listen/links.named, 2026-11-09); its passes keep their request's own names. A piece
    heard with no lead holds its passes as their listener wrote them, in a kept hearing too: they
    are placed in the piece before the vote, as a piece with a lead was when it was heard
    (2026-11-14: voted as written, two passes in minutes and seconds outvoted the right one)."""
    pieces = [replace(p, passes=[placed_in(run, p.end - p.start) for run in p.passes])
              if p.lead_s <= 0 else p for p in pieces]
    voted = named(pieces, [agreed(p.passes) for p in pieces])
    utterances = [u for k, p in enumerate(pieces)
                  for u in shift(voted[k], p.span, request=f"k{k}.v")]
    rounds = max(len(p.passes) for p in pieces)
    passes = [[u for k, p in enumerate(pieces) if n < len(p.passes)
               for u in shift(p.passes[n], p.span, request=f"k{k}.p{n}")] for n in range(rounds)]
    return utterances, passes
