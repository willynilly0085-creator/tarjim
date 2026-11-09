"""Which stretches the tolerant aligner reads again with the skip on (asr/tolerated.py,
2026-11-09).

A run is one line's words said in one breath (agree.run_spans inside each line), so a copy the
listener wrote right after its line is a run of its own and not hidden in the line's score. A
stretch is read again, from AROUND seconds before the run to AROUND after, when:

- the run's strict score is under the clip's floor (agree.clip_baseline) and it is not said over
  another speaker's line (two voices at once score low and prove nothing), every speaker's
  words in the stretch read again;
- or its words are a copy of its own speaker's words placed close by (asr/unplaced.Near.copied),
  wherever it sits: a copy finds its letters in the copy it repeats, so its score does not tell
  it. Such a window reads that speaker's words alone (`Window.speaker`), the other voices' kept
  where they are (asr/reread.py), and what it leaves out is taken only when all of it is such a
  copy; otherwise the first times stay, as they were before the tolerant mode. Until the review
  of 2026-11-09 every voice was read there: on en_refrain_twice x loop_all, S2's line was left
  out as a copy of S1's same words and S1's copy timed onto S2's speech.
"""
from collections.abc import Callable
from itertools import groupby
from typing import NamedTuple

from tarjim.asr.agree import run_spans
from tarjim.asr.unplaced import Near, owners
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

AROUND = 2.0  # seconds either side of a run read again with the skip on

Score = Callable[[list[Word]], float | None]


class Window(NamedTuple):
    low: float  # seconds of the sound read again
    high: float
    speaker: str | None  # a copy's speaker, read alone: only copies may be left out; None all

    @property
    def copies(self) -> bool:
        return self.speaker is not None


def line_runs(words: list[Word], owner: list[int]) -> list[tuple[int, int]]:
    """The runs inside each line, as (first, past) in the words."""
    found: list[tuple[int, int]] = []
    for _, line in groupby(range(len(words)), key=owner.__getitem__):
        indices = list(line)
        first, past = indices[0], indices[-1] + 1
        found += [(first + a, first + b) for a, b in run_spans(words[first:past])]
    return found


def over_another(run: list[Word], lines: list[Utterance]) -> bool:
    who, start, end = run[0].speaker, run[0].start, run[-1].end
    return any(u.speaker != who and u.start < end and u.end > start for u in lines)


class Weak:
    """The runs of one alignment, judged against the clip's floor."""

    def __init__(self, words: list[Word], lines: list[Utterance], floor: float) -> None:
        self.words, self.lines, self.floor = words, lines, floor
        self.owner, self.near = owners(lines), Near(words, lines)

    def copy(self, first: int, past: int) -> bool:
        own = set(range(first, past))
        return self.near.copied(sorted(own), own)

    def judged(self, first: int, past: int, score: Score) -> Window | None:
        run = self.words[first:past]
        value = score(run)
        low = value is not None and value < self.floor and not over_another(run, self.lines)
        if not low and not self.copy(first, past):
            return None
        who = None if low else run[0].speaker
        return Window(run[0].start - AROUND, run[-1].end + AROUND, who)

    def windows(self, score: Score) -> list[Window]:
        """Each run's window, those that meet made one."""
        if len(self.owner) != len(self.words):
            return []
        found: list[Window] = []
        for first, past in line_runs(self.words, self.owner):
            window = self.judged(first, past, score)
            if window is not None:
                joined(found, window)
        return found


def joined(found: list[Window], window: Window) -> None:
    last = found[-1] if found else None
    if last is not None and window.low <= last.high and window.speaker == last.speaker:
        found[-1] = last._replace(high=max(last.high, window.high))
    else:
        found.append(window)
