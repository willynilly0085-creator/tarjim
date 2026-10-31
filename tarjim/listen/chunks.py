"""Long sound is heard in pieces of about 75 seconds, each cut in a pause.

A cloud listener given minutes of sound in one request drifts and leaves speech out: on
2026-10-31 all three passes over a 250-second clip stopped at 178 s and stretched their times to
fill the rest. Short pieces keep every listener close to the sound. A piece's speakers keep the
listener's labels: a tag per piece made one person a new speaker every 75 seconds, and a dub gives
each speaker a voice of their own.
"""
from collections.abc import Callable
from itertools import pairwise

from tarjim.job import checkpoint
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard

CHUNK_SECONDS = 75.0
SEARCH_SHARE = 0.2  # a cut is looked for this share of a piece either side of its target
LONGEST_SEARCH = 30.0
TAIL_SHARE = 0.3  # a last piece shorter than this share of a piece joins the one before it
OVERRUN = 1.0

Span = tuple[float, float]
ListenSpan = Callable[[float, float], Heard]


def chunk_seconds() -> float:
    """The person's setting `listen_chunk_seconds`; 0 hears the whole clip in one request."""
    from tarjim.config import setting

    try:
        chosen = float(setting("listen_chunk_seconds") or CHUNK_SECONDS)
    except ValueError:
        return CHUNK_SECONDS
    return max(chosen, 0.0)


def is_long(duration: float, target: float | None = None) -> bool:
    size = chunk_seconds() if target is None else target
    return size > 0 and duration > size * (1 + TAIL_SHARE)


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


def shift(utterances: list[Utterance], span: Span, tag: str = "") -> list[Utterance]:
    start, end = span
    return [Utterance(u.start + start, min(u.end + start, end + OVERRUN), f"{tag}{u.speaker}",
                      u.text)
            for u in utterances if u.start + start < end + OVERRUN]


def listen_one(span: Span, listen_span: ListenSpan) -> Heard:
    """Each chunk is a step of its own: the person's pause or cancel takes effect before it."""
    checkpoint()
    return listen_span(*span)


def listen_in_chunks(duration: float, regions: list[Span], listen_span: ListenSpan,
                     target: float | None = None) -> Heard:
    pieces = [(span, listen_one(span, listen_span))
              for span in spans(duration, regions, target)]
    utterances = [u for span, heard in pieces for u in shift(heard.utterances, span)]
    rounds = max(len(heard.passes) for _, heard in pieces)
    passes = [[u for span, heard in pieces if k < len(heard.passes)
               for u in shift(heard.passes[k], span)] for k in range(rounds)]
    if len(pieces) > 1:
        print(f"listening: {len(pieces)} pieces, cut in pauses", flush=True)
    return Heard(pieces[0][1].language, utterances, passes)
