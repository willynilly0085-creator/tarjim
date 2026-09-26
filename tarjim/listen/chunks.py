from collections.abc import Callable
from itertools import pairwise

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard

CHUNK_SECONDS = 300.0
SEARCH = 30.0
MIN_TAIL = 60.0
OVERRUN = 1.0

Span = tuple[float, float]
ListenSpan = Callable[[float, float], Heard]


def is_long(duration: float) -> bool:
    return duration > CHUNK_SECONDS + MIN_TAIL


def boundary(target: float, regions: list[Span]) -> float:
    gaps = [(a[1] + b[0]) / 2 for a, b in pairwise(regions) if b[0] > a[1]]
    near = [g for g in gaps if abs(g - target) <= SEARCH]
    return min(near, key=lambda g: abs(g - target)) if near else target


def spans(duration: float, regions: list[Span]) -> list[Span]:
    if not is_long(duration):
        return [(0.0, duration)]
    cuts, target = [], CHUNK_SECONDS
    while target < duration - MIN_TAIL:
        cut = boundary(target, regions)
        cuts.append(cut)
        target = cut + CHUNK_SECONDS
    return list(pairwise([0.0, *cuts, duration]))


def shift(utterances: list[Utterance], span: Span, tag: str) -> list[Utterance]:
    start, end = span
    return [Utterance(u.start + start, min(u.end + start, end + OVERRUN), f"{tag}{u.speaker}",
                      u.text)
            for u in utterances if u.start + start < end + OVERRUN]


def listen_in_chunks(duration: float, regions: list[Span], listen_span: ListenSpan) -> Heard:
    pieces = [(span, listen_span(*span)) for span in spans(duration, regions)]
    tags = [f"c{k}." if len(pieces) > 1 else "" for k in range(len(pieces))]
    utterances = [u for (span, heard), tag in zip(pieces, tags, strict=True)
                  for u in shift(heard.utterances, span, tag)]
    rounds = max(len(heard.passes) for _, heard in pieces)
    passes = [[u for (span, heard), tag in zip(pieces, tags, strict=True)
               if k < len(heard.passes) for u in shift(heard.passes[k], span, tag)]
              for k in range(rounds)]
    return Heard(pieces[0][1].language, utterances, passes)
