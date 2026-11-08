"""Stretches of speech that no line of the transcript covers.

Cloud listeners leave speech out, at the end of a clip most of all: on 2026-10-31 every pass over
a 250-second clip stopped at 178 s, while the sound held speech to 240 s and the listener on this
computer heard it. The check runs after the times were corrected against the local words
(asr/anchor.py), so a listener's late times are not taken for missing speech. Speech is what the
voice detector found, together with the words this computer heard (either may be missing).
"""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, replace

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

GAP_SECONDS = 2.0  # this much speech with no line is speech left out, not a breath
EDGE = 0.5  # a line's times are rough by about this much
JOIN = 1.0  # speech pieces this close belong to one stretch
# what listen/repair.py says of a stretch nothing filled (moved here with `described` and
# `still_left` on 2026-11-08, to make room in repair.py; it still offers them)
NOT_REPAIRED = "not repaired"
NOT_ASKED = "not asked again"

Span = tuple[float, float]


@dataclass(frozen=True)
class Gap:
    start: float
    end: float
    speech: float  # seconds of speech inside
    words: list[Word]  # what this computer heard inside
    # no listener heard it and it is not asked about again: still listed on the job, but it does
    # not stop the transcript being kept (2026-11-08: it was dropped, and the job looked whole)
    given_up: bool = False


def open_gaps(left: list[Gap]) -> list[Gap]:
    """The stretches that are still asked about on the next run."""
    return [gap for gap in left if not gap.given_up]


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


def local_only(heard: list[Span], detected: list[Span]) -> int:
    """Stretches only the local words call speech, longer than a line's times are rough: what
    the local words add to the voice detector's speech (counted, tarjim/guards.py)."""
    regions = merged(detected, 0.0)
    lows, highs = [low for low, _ in regions], [high for _, high in regions]
    return sum(b - a > EDGE for start, end in merged(heard, JOIN) for a, b in outside(
        (start, end), regions[bisect_right(highs, start):bisect_left(lows, end)]))


def speech_of(hearing: Hearing) -> list[Span]:
    heard = [(w.start, w.end) for w in hearing.local if w.end > w.start]
    guards.fired("coverage.local_only", local_only(heard, hearing.regions))
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


def described(gap: Gap) -> str:
    said = f"{len(gap.words)} local words" if gap.words else "no words"
    return f"gap {gap.start:.1f}-{gap.end:.1f} s ({gap.speech:.1f} s of speech, {said})"


def still_left(gap: Gap, outcome: str) -> list[Gap]:
    """The stretch, when nothing filled it: to be asked again, or given up but still listed."""
    if outcome == NOT_REPAIRED:
        return [gap]
    return [replace(gap, given_up=True)] if NOT_ASKED in outcome else []
