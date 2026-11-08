"""How long each subtitle stays on screen (2026-11-08).

Two promises hold for every subtitle: it stays up at least rules.shortest (min_duration and
min_readable both), and it ends rules.min_gap before the next one starts. Before, the end was
cut to fit, so a line squeezed by the next one was shown for a microsecond and a line just
before a shot change flashed, and the next line was pushed up to 0.9 s late to make room. When
the two promises clash, this tries, in order: running on into the gap after it, starting up to
LEAD_IN early (never across a shot change or into the line before), joining a neighbour (one
speaker becomes one part, two become an exchange), running past the shot change, and only
last, holding the line for rules.shortest and starting the next one after it.
"""
from dataclasses import dataclass

from tarjim.dialogue import MAX_SPEAKERS, fits_one_line, last_end
from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules
from tarjim.speakers import who

LEAD_IN = 0.2
TOLERANCE = 1e-9
NEVER = float("inf")

Parts = list[list[Word]]


@dataclass(frozen=True)
class Frame:
    rules: Rules
    cuts: list[float]


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
    joined = join_around(cues, index, frame)
    if joined is not None:
        return joined
    if not fit(cue, floor, ceiling, frame):
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


def joinable(first: Cue, second: Cue, frame: Frame) -> bool:
    if not (first.words and second.words) or first.text or second.text:
        return False
    rules, parts = frame.rules, joined_parts(first, second, frame)
    span = max(spoken_end(first), spoken_end(second)) - first.start
    if len(parts) > MAX_SPEAKERS or span > rules.max_duration + TOLERANCE:
        return False
    if cut_between(first, second, frame.cuts) and span > rules.cut_dialogue_span:
        return False
    if len(parts) == 1:
        return len(join_words(parts[0])) <= rules.max_source_chars
    return all(fits_one_line(part, rules) for part in parts)


def joined_parts(first: Cue, second: Cue, frame: Frame) -> Parts:
    head, tail = first.parts or [first.words], second.parts or [second.words]
    if same_voice(head[-1], tail[0], cut_between(first, second, frame.cuts)):
        return [*head[:-1], head[-1] + tail[0], *tail[1:]]
    return [*head, *tail]


def same_voice(before: list[Word], after: list[Word], at_cut: bool) -> bool:
    """Labelled words say who speaks; without labels a shot change marks a new speaker, as the
    cue builder reads them (segment.speaker_changed)."""
    if any(word.speaker for word in before + after):
        return who(before[0].speaker) == who(after[0].speaker)
    return not at_cut


def joined(first: Cue, second: Cue, frame: Frame) -> Cue:
    parts = joined_parts(first, second, frame)
    words = [word for part in parts for word in part]
    return Cue(first.start, last_end(words), words, parts=[list(part) for part in parts])


def cut_between(first: Cue, second: Cue, cuts: list[float]) -> bool:
    return any(spoken_end(first) <= cut <= second.words[0].start for cut in cuts)


def spoken_end(cue: Cue) -> float:
    return last_end(cue.words) if cue.words else cue.end


def next_cut(cuts: list[float], after: float) -> float:
    return min((cut for cut in cuts if cut > after), default=NEVER)


def last_cut(cuts: list[float], at: float) -> float:
    return max((cut for cut in cuts if cut <= at), default=-NEVER)
