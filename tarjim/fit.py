"""How long each subtitle stays on screen (2026-11-08).

Two promises hold for every subtitle: it stays up at least rules.shortest (min_duration and
min_readable both), and it ends rules.min_gap before the next one starts. Before, the end was
cut to fit, so a line squeezed by the next one was shown for a microsecond and a line just
before a shot change flashed, and the next line was pushed up to 0.9 s late to make room. When
the two promises clash, this tries, in order: running on into the gap after it, starting up to
LEAD_IN early (never across a shot change or into the line before), joining a neighbour (one
speaker becomes one part, two become an exchange), running past the shot change, letting the
next line come up at most LATE_START after its first word, sharing the screen with part of a
neighbouring turn (crowded.handed), and only last, holding the line for rules.shortest and
starting the next one after it.
"""
from tarjim.crowded import handed
from tarjim.joins import TOLERANCE, Frame, joinable, joined, spoken_end
from tarjim.models import Cue
from tarjim.rules import Rules

LEAD_IN = 0.2
# The most a subtitle comes up after its first word to leave the one before it time, since
# 2026-11-08: before, a one-word reply held for rules.shortest pushed the answer after it 0.56 s
# past its first word. Only a line too short to read waits for it (waited): bringing the next
# line up late whenever two voices crossed moved what was not shown from one line's end to the
# next one's start, and kept the two from the subtitle that showed them both.
LATE_START = 0.2
NEVER = float("inf")

__all__ = ["Frame", "fit_timing"]


def fit_timing(cues: list[Cue], rules: Rules, cuts: list[float] | None = None) -> list[Cue]:
    frame = Frame(rules, sorted(cuts or []))
    placed = sorted(cues, key=lambda cue: cue.start)
    index = 0
    while index < len(placed):
        index = settle(placed, index, frame)
    return placed


def settle(cues: list[Cue], index: int, frame: Frame) -> int:
    """Places one subtitle and says which to place next: the same one again after a join."""
    cue, gap = cues[index], frame.rules.min_gap
    floor = cues[index - 1].end + gap if index else 0.0
    ceiling = cues[index + 1].start - gap if index + 1 < len(cues) else NEVER
    if fit(cue, floor, min(ceiling, next_cut(frame.cuts, spoken_end(cue))), frame):
        return index + 1
    joined_at = join_around(cues, index, frame)
    if joined_at is not None:
        return joined_at
    if fit(cue, floor, ceiling, frame):
        return index + 1
    return crowded(cues, index, frame, floor)


def crowded(cues: list[Cue], index: int, frame: Frame, floor: float) -> int:
    if waited(cues, index, frame, floor):
        return index + 1
    handed_at = handed(cues, index, frame)
    if handed_at is not None:
        return handed_at
    hold(cues, index, frame.rules)
    return index + 1


def fit(cue: Cue, floor: float, ceiling: float, frame: Frame) -> bool:
    rules = frame.rules
    for start in (cue.start, lead_in(cue.start, floor, ceiling, frame)):
        end = shown_until(cue, start, ceiling, rules)
        if end - start >= rules.shortest - TOLERANCE:
            cue.start, cue.end = start, end
            return True
    return False


def lead_in(start: float, floor: float, ceiling: float, frame: Frame) -> float:
    earliest = max(start - LEAD_IN, min(floor, start), last_cut(frame.cuts, start))
    return max(earliest, min(start, ceiling - frame.rules.shortest))


def shown_until(cue: Cue, start: float, ceiling: float, rules: Rules) -> float:
    wanted = max(spoken_end(cue) + rules.linger, start + rules.shortest)
    return min(wanted, start + rules.max_duration, ceiling)


def waited(cues: list[Cue], index: int, frame: Frame, floor: float) -> bool:
    """The line is read in full if the next one comes up LATE_START after its first word."""
    if index + 1 >= len(cues) or not cues[index + 1].words:
        return False
    cue, following, rules = cues[index], cues[index + 1], frame.rules
    ceiling = following.start - rules.min_gap
    latest = pushed_to(cues, index + 1, first_said(following) + LATE_START) - rules.min_gap
    if not fit(cue, floor, max(ceiling, latest), frame):
        return False
    cue.end = min(cue.end, max(cue.start + rules.shortest, ceiling))
    following.start = max(following.start, cue.end + rules.min_gap)
    return True


def pushed_to(cues: list[Cue], index: int, at: float) -> float:
    """How late the subtitle at index may come up: at, and never after the one after it."""
    return min(at, cues[index + 1].start) if index + 1 < len(cues) else at


def first_said(cue: Cue) -> float:
    return min(word.start for word in cue.words)


def hold(cues: list[Cue], index: int, rules: Rules) -> None:
    """The last resort: the line stays long enough to read and the next one waits for it."""
    cue = cues[index]
    cue.end = cue.start + rules.shortest
    if index + 1 < len(cues):
        following = cues[index + 1]
        following.start = max(following.start, cue.end + rules.min_gap)


def join_around(cues: list[Cue], index: int, frame: Frame) -> int | None:
    if index + 1 < len(cues) and joinable(cues[index], cues[index + 1], frame):
        cues[index:index + 2] = [joined(cues[index], cues[index + 1], frame)]
        return index
    if index and joinable(cues[index - 1], cues[index], frame):
        cues[index - 1:index + 1] = [joined(cues[index - 1], cues[index], frame)]
        return index - 1
    return None


def next_cut(cuts: list[float], after: float) -> float:
    return min((cut for cut in cuts if cut > after), default=NEVER)


def last_cut(cuts: list[float], at: float) -> float:
    return max((cut for cut in cuts if cut <= at), default=-NEVER)
