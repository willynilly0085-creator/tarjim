"""Stretches of speech that no line of the transcript covers.

Cloud listeners leave speech out, at the end of a clip most of all: on 2026-10-31 every pass over
a 250-second clip stopped at 178 s, while the sound held speech to 240 s and the listener on this
computer heard it. The check runs after the times were corrected against the local words
(asr/anchor.py), so a listener's late times are not taken for missing speech. Speech is what the
voice detector found, together with the words this computer heard (either may be missing).
"""
from dataclasses import dataclass

from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

GAP_SECONDS = 2.0  # this much speech with no line is speech left out, not a breath
EDGE = 0.5  # a line's times are rough by about this much
JOIN = 1.0  # speech pieces this close belong to one stretch

Span = tuple[float, float]


@dataclass(frozen=True)
class Gap:
    start: float
    end: float
    speech: float  # seconds of speech inside
    words: list[Word]  # what this computer heard inside


@dataclass(frozen=True)
class Hearing:
    utterances: list[Utterance]
    local: list[Word]
    regions: list[Span]  # the voice detector's speech; none when it could not run


def gap_seconds() -> float:
    """The person's setting `coverage_gap_seconds`."""
    from tarjim.config import setting

    try:
        return max(float(setting("coverage_gap_seconds") or GAP_SECONDS), 0.1)
    except ValueError:
        return GAP_SECONDS


def merged(spans: list[Span], join: float) -> list[Span]:
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start - out[-1][1] <= join:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def outside(span: Span, covered: list[Span]) -> list[Span]:
    pieces, (start, end) = [], span
    for low, high in covered:
        if high <= start or low >= end:
            continue
        if low > start:
            pieces.append((start, low))
        start = max(start, high)
    return [*pieces, (start, end)] if end > start else pieces


def speech_of(hearing: Hearing) -> list[Span]:
    heard = [(w.start, w.end) for w in hearing.local if w.end > w.start]
    return merged([*hearing.regions, *heard], 0.0)


def uncovered(hearing: Hearing) -> list[list[Span]]:
    covered = merged([(u.start - EDGE, u.end + EDGE) for u in hearing.utterances], 0.0)
    pieces = [p for span in speech_of(hearing) for p in outside(span, covered)]
    groups: list[list[Span]] = []
    for piece in sorted(pieces):
        if groups and piece[0] - groups[-1][-1][1] <= JOIN:
            groups[-1].append(piece)
        else:
            groups.append([piece])
    return groups


def gaps(hearing: Hearing, least: float | None = None) -> list[Gap]:
    shortest = gap_seconds() if least is None else least
    found = []
    for group in uncovered(hearing):
        start, end = group[0][0], group[-1][1]
        inside = [w for w in hearing.local if start <= (w.start + w.end) / 2 <= end]
        speech = sum(b - a for a, b in group)
        if speech >= shortest:
            found.append(Gap(start, end, speech, inside))
    return found
