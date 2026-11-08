"""The words this computer heard, used only where the sound confirms them (2026-11-08).

The listener on this computer (Qwen3-ASR) can hear the right words at the wrong times. On the
Arabic bench clips (2026-11-08) its times drifted up to 11 s early and half its words had no length
at all; the anchor trusted them because their text matched and moved right lines 10 s early, the
aligner squeezed those lines, the coverage check asked again about the speech they left, and the
same lines came back twice. So before anything uses them (the anchor, fuse, best_heard, the
coverage check, the fills and settle.trusted), each run of them is looked for in the sound at its
own time only (asr/agree.run_score, never wider than its SLACK), in the letters the aligner heard in
the whole clip once (asr/letters.Letters), which timing reads again for free.

A run (at most WORDS words: a run of 11 timed 4 s early halfway through still scored 0.71, its
first half found) is kept when it is found (agree.FOUND) and not far below the clip's own found
runs; a word with no length, or longer than anyone says it, is never kept; a run with too few
letters to tell alone goes with the judged runs either side of it (a lone word 6 s early sat
between runs not found); where most of a stretch's words are not found, none of it is kept;
and where hardly any are found in the whole clip (a script the aligner barely reads), none is used
at all, said in the log. When nothing can be looked for (no letters, or a stand-in aligner with no
ears), the words are used as before, and the log says they could not be checked.
"""
from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from itertools import accumulate
from statistics import median

import numpy as np

from tarjim.asr.agree import FOUND, Tokens, run_score, runs
from tarjim.asr.spread import longest
from tarjim.models import Word

NEAR = 0.85  # of the clip's median found run (by words): a run found less is not kept
STRETCH = 30.0  # seconds of runs around a run judged with it
MOST = 0.5  # share of a stretch's judged words not found that drops the whole stretch
TINY = 0.2  # share of the clip's judged words found under which none is used
LONGEST = 2.0  # times the longest a word is said (spread.longest): longer is no time to say it
WORDS = 6  # words of a run judged together
LETTERS = 8  # letters a run needs to be judged on its own; fewer go with their stretch

Judged = tuple[list[Word], float | None]  # a run, and its score; None: not judged alone


@dataclass(frozen=True)
class Kept:
    words: list[Word]
    heard: int  # the words this computer heard
    no_length: int = 0  # with no length, or longer than anyone says them
    not_found: int = 0  # in runs not found where they are timed
    stretch: int = 0  # in stretches whose words were mostly not found
    unused: int = 0  # all of them, when hardly any were found in the whole clip
    checked: bool = True  # False: nothing could be looked for, so all are used


def plausible(word: Word) -> bool:
    return 0.0 < word.end - word.start <= LONGEST * longest(word.text)


def unchecked(words: list[Word]) -> Kept:
    """The words when the sound cannot tell: all used, but never one with no length."""
    sane = [w for w in words if plausible(w)]
    return Kept(sane, len(words), len(words) - len(sane), checked=False)


def scored(logp: np.ndarray, words: list[Word], tokens: Tokens) -> list[Judged]:
    """Each run with its score where it is timed; a run with fewer letters than LETTERS (or than
    the clip's longest run, when every run is short) is not judged alone."""
    found = [run[k:k + WORDS] for run in runs(words) for k in range(0, len(run), WORDS)]
    letters = [sum(len(tokens(w.text)) for w in run) for run in found]
    need = max(1, min(LETTERS, max(letters, default=0)))
    return [(run, run_score(logp, run, tokens) if count >= need else None)
            for run, count in zip(found, letters, strict=True)]


def bar(judged: list[Judged]) -> float:
    """The least score kept: FOUND, or near the clip's own found runs, weighted by words."""
    found = [s for run, s in judged if s is not None and s >= FOUND for _ in run]
    return max(FOUND, NEAR * median(found)) if found else FOUND


def sums(values: Iterable[int]) -> list[int]:
    return list(accumulate(values, initial=0))


def failing(judged: list[Judged], found: list[bool | None]) -> list[bool]:
    """Each run's stretch: whether most of its judged words, or all when none is, are not found."""
    starts = [run[0].start for run, _ in judged]
    sizes = list(zip([len(run) for run, _ in judged], found, strict=True))
    told = sums(size if ok is not None else 0 for size, ok in sizes)
    lost = sums(size if ok is False else 0 for size, ok in sizes)
    flags = []
    for start in starts:
        low = bisect_left(starts, start - STRETCH / 2)
        high = bisect_right(starts, start + STRETCH / 2)
        judged_here = told[high] - told[low]
        flags.append(not judged_here or lost[high] - lost[low] > MOST * judged_here)
    return flags


def before(found: list[bool | None]) -> list[bool]:
    """Whether the nearest judged run before each run was found (True when there is none)."""
    last, seen = True, []
    for ok in found:
        seen.append(last)
        last = last if ok is None else ok
    return seen


def vouched(found: list[bool | None]) -> list[bool]:
    """Each run found; one too short to judge alone when the judged runs either side of it are:
    a lone word 6 s early sat between runs not found (2026-11-08)."""
    after = before(found[::-1])[::-1]
    return [ok if ok is not None else first and last
            for ok, first, last in zip(found, before(found), after, strict=True)]


def chosen(judged: list[Judged], heard: int, dropped: int) -> Kept:
    """The runs found, outside the stretches mostly not found."""
    least = bar(judged)
    found = [None if s is None else s >= least for _, s in judged]
    words: list[Word] = []
    not_found = stretch = 0
    for (run, _), fails, ok in zip(judged, failing(judged, found), vouched(found), strict=True):
        if fails:
            stretch += len(run)
        elif not ok:
            not_found += len(run)
        else:
            words.extend(run)
    return Kept(words, heard, dropped, not_found, stretch)


def confirmed(logp: np.ndarray, words: list[Word], tokens: Tokens) -> Kept:
    """The words found in the sound where they are timed (the clip's letters `logp`)."""
    sane = sorted((w for w in words if plausible(w)), key=lambda w: w.start)
    dropped = len(words) - len(sane)
    judged = scored(logp, sane, cache(tokens))
    told = sum(len(run) for run, s in judged if s is not None)
    if not told:  # no letters to look for: used as before, those with no length aside
        return unchecked(words)
    found = sum(len(run) for run, s in judged if s is not None and s >= FOUND)
    if found < TINY * told:
        return Kept([], len(words), dropped, unused=len(sane))
    return chosen(judged, len(words), dropped)
