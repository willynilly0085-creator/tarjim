"""How a clip's subtitles stand against what was said: counted, not judged by eye.

Every complaint about the subtitles so far came down to a few things that can be counted:
speech with no subtitle on screen, a subtitle shown well before or after its words are said,
the same words shown twice, a subtitle crammed with more words than its time allows, and
subtitles that stop before the speech does. The yardstick is the words this computer heard on
its own, with times taken from the sound: what a cloud listener wrote is measured against it.
"""
import re
from bisect import bisect_right
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import accumulate

from tarjim.models import Word

SLACK = 0.3  # a word this close to a subtitle is shown with it
RUN_GAP = 1.5  # unshown words this close together are one stretch of speech
RUN_WORDS = 3  # a stretch shorter than this is a stray word, not speech left out
OFF = 2.0  # seconds between where a subtitle is shown and where its words are said
REACH = 40.0  # how far from a subtitle its words are looked for
MATCH = 3  # words matched in a row before a place counts
RUSHED = 5.5  # words a second: nobody speaks faster, so more means words piled on an instant
REPEAT = 20.0  # a subtitle repeating one this recent shows the same words twice
TWICE = 2  # times the speech says the repeated words, when it really is said again
LATE = 1.5  # seconds of speech after the last subtitle that count as the subtitles stopping


@dataclass(frozen=True)
class Shown:
    start: float
    end: float
    source: str


@dataclass(frozen=True)
class Measures:
    words: int  # the yardstick's words (0: nothing to measure against)
    unshown: float  # seconds of speech, in stretches, with no subtitle on screen
    lost: int  # words in those stretches that no subtitle has anywhere
    off: int  # subtitles shown OFF seconds or more from where their words are said
    checked: int  # subtitles whose place could be found in the yardstick
    doubled: int  # subtitles repeating one just before, where the speech says it once
    rushed: int  # subtitles with more words than their time allows
    stopped: float  # seconds of speech after the last subtitle


def norm(text: str) -> str:
    return re.sub(r"[^\w']", "", text.lower())


def tokens(source: str) -> list[str]:
    return [t for t in (norm(part) for part in source.replace("||", " ").split()) if t]


def outside(words: list[Word], shown: list[Shown]) -> list[Word]:
    """The words no subtitle is on screen for."""
    spans = sorted((s.start - SLACK, s.end + SLACK) for s in shown)
    starts = [a for a, _ in spans]
    reach = list(accumulate((b for _, b in spans), max))  # the furthest end so far
    return [w for w in words if (k := bisect_right(starts, w.start) - 1) < 0 or reach[k] < w.start]


def stretches(words: list[Word]) -> list[list[Word]]:
    runs: list[list[Word]] = []
    for word in words:
        if runs and word.start - runs[-1][-1].end < RUN_GAP:
            runs[-1].append(word)
        else:
            runs.append([word])
    return [run for run in runs if len(run) >= RUN_WORDS]


def grams(said: list[str], size: int = MATCH) -> set[tuple[str, ...]]:
    return {tuple(said[k:k + size]) for k in range(len(said) - size + 1)}


def is_lost(run: list[Word], everywhere: set[tuple[str, ...]]) -> bool:
    mine = grams([norm(w.text) for w in run])
    return not mine or len(mine & everywhere) * 2 < len(mine)


def unshown(words: list[Word], shown: list[Shown]) -> tuple[float, int]:
    """Seconds of speech with no subtitle, and how many of its words appear nowhere."""
    runs = stretches(outside(words, shown))
    everywhere = grams([t for s in shown for t in tokens(s.source)])
    seconds = sum(run[-1].end - run[0].start for run in runs)
    return seconds, sum(len(run) for run in runs if is_lost(run, everywhere))


def place(one: Shown, words: list[Word]) -> float | None:
    """How far the subtitle is shown from where its first words are said, or None."""
    mine = tokens(one.source)
    near = [w for w in words if one.start - REACH <= w.start <= one.end + REACH]
    if len(mine) <= MATCH or not near:
        return None
    blocks = SequenceMatcher(None, mine, [norm(w.text) for w in near], autojunk=False)
    shifts = [one.start - near[b.b].start - 0.3 * b.a for b in blocks.get_matching_blocks()
              if b.size >= MATCH and b.a < MATCH]
    return min(shifts, key=abs) if shifts else None


def misplaced(words: list[Word], shown: list[Shown]) -> tuple[int, int]:
    found = [s for s in (place(one, words) for one in shown) if s is not None]
    return sum(1 for s in found if abs(s) >= OFF), len(found)


def said_times(phrase: tuple[str, ...], words: list[Word], start: float, end: float) -> int:
    near = [norm(w.text) for w in words if start - 3 <= w.start <= end + 3]
    return sum(1 for k in range(len(near)) if tuple(near[k:k + len(phrase)]) == phrase)


def repeats(one: Shown, before: list[Shown]) -> Shown | None:
    mine = grams(tokens(one.source), 4)
    for earlier in reversed(before):
        if one.start - earlier.start <= REPEAT and mine and \
                len(mine & grams(tokens(earlier.source), 4)) * 5 >= len(mine) * 3:
            return earlier
    return None


def doubled(words: list[Word], shown: list[Shown]) -> int:
    count = 0
    for k, one in enumerate(shown):
        earlier = repeats(one, shown[max(0, k - 3):k])
        if earlier is not None and (not words or said_times(
                tuple(tokens(one.source)[:4]), words, earlier.start, one.end) < TWICE):
            count += 1
    return count


def rushed(shown: list[Shown]) -> int:
    return sum(1 for s in shown if len(tokens(s.source)) > RUSHED * max(s.end - s.start, 0.4))


def stopped(words: list[Word], shown: list[Shown]) -> float:
    if not words:
        return 0.0
    last = max((s.end for s in shown), default=0.0)
    late = words[-1].end - last
    return round(late, 1) if late > LATE else 0.0


def measured(shown: list[Shown], words: list[Word]) -> Measures:
    seconds, lost = unshown(words, shown)
    off, checked = misplaced(words, shown)
    return Measures(len(words), round(seconds, 1), lost, off, checked, doubled(words, shown),
                    rushed(shown), stopped(words, shown))
