"""Stretches of speech that no line of the transcript covers.

Cloud listeners leave speech out, at the end of a clip most of all: on 2026-10-31 every pass over
a 250-second clip stopped at 178 s, while the sound held speech to 240 s and the listener on this
computer heard it. The check runs after the times were corrected against the local words
(asr/anchor.py), so a listener's late times are not taken for missing speech. Speech is what the
voice detector found, together with the words this computer heard (either may be missing).

Since 2026-11-09 speech is the clip's speech map (asr/speechmap.py) when one is given, so a stretch
is judged the same with or without the local listener; one only the local words call speech is
given up (listed, never asked about) when the sound holds no speech there (listen/bysound.py).
"""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field, replace

from tarjim import guards
from tarjim.asr.speechmap import SpeechMap
from tarjim.listen.bysound import NO_SOUND, by_sound
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

GAP_SECONDS = 2.0  # this much speech with no line is speech left out, not a breath
EDGE = 0.5  # a line's times are rough by about this much
JOIN = 1.0  # speech pieces this close belong to one stretch
# what listen/repair.py says of a stretch nothing filled (here since 2026-11-08; it offers them)
NOT_REPAIRED = "not repaired"
NOT_ASKED = "not asked again"
# seconds around a stretch where local words left out as unconfirmed say the local listener heard
# speech there after all, timed elsewhere: Qwen drifted up to 11 s on the Arabic bench (2026-11-08)
DOUBT = 15.0
UNSPOKEN = f"no speech here by the sound; {NOT_ASKED}, left as it is"

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
    # what the speech map says of a stretch only the local words call speech (2026-11-09)
    sound: str = ""

    @property
    def unspoken(self) -> bool:
        return self.sound.startswith(NO_SOUND)


def open_gaps(left: list[Gap]) -> list[Gap]:
    """The stretches that are still asked about on the next run."""
    return [gap for gap in left if not gap.given_up]


@dataclass(frozen=True)
class Hearing:
    utterances: list[Utterance]
    local: list[Word]
    regions: list[Span]  # the voice detector's speech; none when it could not run
    # where the local words the sound did not confirm were timed (listen/opinion.doubted)
    doubted: list[Span] = field(default_factory=list)
    # what fills a stretch: the local words kept ones hold in place (listen/opinion.held,
    # 2026-11-09); none given, the kept ones alone
    held: list[Word] = field(default_factory=list)
    # the clip's speech map (listen/clipmap.py, 2026-11-09); None: the detector and local words
    map: SpeechMap | None = None


def heard_nothing(hearing: Hearing, gap: Gap) -> bool:
    """The local listener ran and heard no words in the stretch. Since 2026-11-08 a stretch near
    local words left out as unconfirmed is not one: they were heard, timed off, so it stays open
    as with the local listener off, where before A1's review it was closed as heard by no one.
    With the speech map no stretch is one (2026-11-09): every stretch with no local words is the
    map's own speech, open whether the local listener ran or not, as it is with it off."""
    return hearing.map is None and bool(hearing.local) and not gap.words and not any(
        a - DOUBT < gap.end and b + DOUBT > gap.start for a, b in hearing.doubted)


def gap_seconds() -> float:
    """The job's listen.gap_seconds (2026-11-09); TARJIM_COVERAGE_GAP_SECONDS still sets it."""
    import os

    from tarjim.prefs.active import active

    raw = os.environ.get("TARJIM_COVERAGE_GAP_SECONDS", "")
    if not raw:
        return float(active().listen.gap_seconds)
    try:
        return max(float(raw), 0.1)
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


def sounded(hearing: Hearing) -> list[Span]:
    """What the sound calls speech: the map's, else the voice detector's."""
    return list(hearing.regions) if hearing.map is None else hearing.map.speech()


def speech_of(hearing: Hearing) -> list[Span]:
    heard = [(w.start, w.end) for w in hearing.local if w.end > w.start]
    sound = sounded(hearing)
    guards.fired("coverage.local_only", local_only(heard, sound))
    return merged([*sound, *heard], 0.0)


def covered_by(hearing: Hearing) -> list[Span]:
    return merged([(u.start - EDGE, u.end + EDGE) for u in hearing.utterances], 0.0)


def uncovered(hearing: Hearing) -> list[list[Span]]:
    covered = covered_by(hearing)
    pieces = [p for span in speech_of(hearing) for p in outside(span, covered)]
    groups: list[list[Span]] = []
    for piece in sorted(pieces):
        if groups and piece[0] - groups[-1][-1][1] <= JOIN:
            groups[-1].append(piece)
        else:
            groups.append([piece])
    return groups


def gap_of(hearing: Hearing, group: list[Span], covered: list[Span],
           shortest: float) -> Gap | None:
    """The stretch as a gap, when it is one. With a map its own speech decides, padded, or the
    local words past it by more than a line's times are rough, judged by the sound (2026-11-09):
    before, the local words decided whether 1.9 s of the map's speech was a gap."""
    speech = sum(b - a for a, b in group)
    sound, enough = "", speech >= shortest
    if hearing.map is not None:
        sound, mapped = by_sound(hearing.map, group, covered, shortest)
        enough = mapped >= shortest or (enough and speech - mapped > EDGE)
    if not enough:
        return None
    start, end = group[0][0], group[-1][1]
    heard = hearing.held or hearing.local  # held words fill, the kept ones else (2026-11-09)
    inside = [w for w in heard if start <= (w.start + w.end) / 2 <= end]
    return Gap(start, end, speech, inside, sound=sound)


def gaps(hearing: Hearing, least: float | None = None) -> list[Gap]:
    shortest = gap_seconds() if least is None else least
    covered = covered_by(hearing)
    return [gap for group in uncovered(hearing)
            if (gap := gap_of(hearing, group, covered, shortest)) is not None]


def described(gap: Gap) -> str:
    said = f"{len(gap.words)} local words" if gap.words else "no words"
    sound = f"; {gap.sound}" if gap.sound else ""
    return f"gap {gap.start:.1f}-{gap.end:.1f} s ({gap.speech:.1f} s of speech, {said}{sound})"


def still_left(gap: Gap, outcome: str) -> list[Gap]:
    """The stretch, when nothing filled it: to be asked again, or given up but still listed."""
    if outcome == NOT_REPAIRED:
        return [gap]
    return [replace(gap, given_up=True)] if NOT_ASKED in outcome else []
