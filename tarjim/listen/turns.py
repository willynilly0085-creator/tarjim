"""Windows of steady speech, each with its voice print (2026-11-09).

A line's one print says whose it is only as a whole, and a whole line is the unit the listener
can get wrong. Since 2026-11-09 the voice check also hears each speaker in windows of WINDOW
seconds, HOP apart, inside every stretch of a line STEADY long or more that only its speaker
says (no word of another speaker over it): a print of a short stretch inside one person's talk
is that person's voice, never two voices mixed. A long clip gets a longer hop, so there are
never more than MAX_WINDOWS (about 24 s of prints on the processor, measured 2026-11-09 at 2
threads, 20 ms a window); a stretch shorter than WINDOW is one window as long as the stretch.
A line with no window (shorter than STEADY, or talked over) is glimpsed once, in its longest
stretch of its speaker alone when that is GLIMPSE long or more: too little to make a voice from,
enough to say which voice it leans to (listen/windowed.py).
"""
from bisect import bisect_left
from typing import Any, NamedTuple

import numpy as np

from tarjim.asr.voiceprint import RATE
from tarjim.models import Word
from tarjim.speakers import Line, lines, span, who

WINDOW = 2.0  # seconds of sound in one print
HOP = 1.0  # seconds between the starts of two windows of one line
STEADY = 1.5  # seconds: shorter stretches are not heard in windows (whose.STEADY)
MAX_WINDOWS = 1200  # prints in one clip at most
EDGE = 1e-6  # seconds: a window may end this much past its line by rounding
GLIMPSE = 1.0  # seconds: a line with no window is printed once in a stretch this long
GLIMPSES = 300  # such prints in one clip at most (with the windows, about 28 s of prints)


class Window(NamedTuple):
    """One print of one speaker's steady talk: its line, its time, the label it was heard with."""

    line: Line
    start: float
    end: float
    label: str
    vec: np.ndarray


class Spot(NamedTuple):
    line: Line
    start: float
    end: float


class Said(NamedTuple):
    """The clip's words in the order they start, and those starts, to find a time's words."""

    words: list[Word]
    starts: list[float]
    longest: float


def said(words: list[Word]) -> Said:
    ordered = sorted(words, key=lambda w: w.start)
    return Said(ordered, [w.start for w in ordered],
                max((w.end - w.start for w in words), default=0.0))


def others(heard: Said, begin: float, end: float, own: str) -> list[tuple[float, float]]:
    """When words of another speaker than own are said between begin and end, in order."""
    first = bisect_left(heard.starts, begin - heard.longest)
    return [(max(w.start, begin), min(w.end, end))
            for w in heard.words[first:bisect_left(heard.starts, end)]
            if w.speaker and who(w.speaker) != own and w.start < end and w.end > begin]


def free(heard: Said, begin: float, end: float, own: str) -> list[tuple[float, float]]:
    """The stretches from begin to end that no other speaker's word is said over."""
    found, at = [], begin
    for start, stop in others(heard, begin, end, own):
        if start > at:
            found.append((at, start))
        at = max(at, stop)
    return [*found, (at, end)] if end > at else found


def owned(words: list[Word]) -> list[Spot]:
    """Each line's stretches STEADY long or more that only its speaker says (2026-11-09: a
    line another speaker talks over at its end is still heard where it is alone)."""
    heard = said(words)
    found = []
    for line in lines(words):
        own = words[line[0]].speaker
        found += [Spot(line, start, stop) for start, stop in free(heard, *span(words, line),
                                                                 who(own))
                  if own and stop - start >= STEADY]
    return found


def hop(speech_s: float) -> float:
    """HOP, or longer when the speech would make more than MAX_WINDOWS windows."""
    return max(HOP, speech_s / MAX_WINDOWS)


def in_line(line: Line, begin: float, end: float, step: float) -> list[Spot]:
    if end - begin < WINDOW:
        return [Spot(line, begin, end)]
    count = int((end - begin - WINDOW + EDGE) // step) + 1
    return [Spot(line, begin + k * step, begin + k * step + WINDOW) for k in range(count)]


def spots(steady: list[Spot]) -> list[Spot]:
    """Where the windows are, MAX_WINDOWS at most, taken evenly when there would be more."""
    step = hop(sum(s.end - s.start for s in steady))
    found = [w for s in steady for w in in_line(s.line, s.start, s.end, step)]
    if len(found) <= MAX_WINDOWS:
        return found
    keep = np.linspace(0, len(found) - 1, MAX_WINDOWS).round().astype(int)
    return [found[k] for k in sorted(set(keep.tolist()))]


def glimpses(words: list[Word], steady: list[Spot]) -> list[Spot]:
    """Each line with no window, at its longest stretch only its speaker says when that is
    GLIMPSE long or more, GLIMPSES at most, taken evenly when there would be more."""
    heard, taken = said(words), {s.line for s in steady}
    found = []
    for line in lines(words):
        own = words[line[0]].speaker
        stretches = free(heard, *span(words, line), who(own)) if own and line not in taken else []
        best = max(stretches, key=lambda s: s[1] - s[0], default=(0.0, 0.0))
        if best[1] - best[0] >= GLIMPSE:
            found.append(Spot(line, *best))
    keep = np.linspace(0, len(found) - 1, min(len(found), GLIMPSES)).round().astype(int)
    return [found[k] for k in sorted(set(keep.tolist()))]


def printed(words: list[Word], wav: Any, where: list[Spot]) -> list[Window]:
    from tarjim.asr.voiceprint import print_of

    return [Window(s.line, s.start, s.end, who(words[s.line[0]].speaker),
                   print_of(wav[int(s.start * RATE):int(s.end * RATE)])) for s in where]


def windows(words: list[Word], wav: Any) -> tuple[list[Window], list[Window]]:
    """The windows of the clip's steady talk, and the glimpses of its other lines, each with
    its print (sound at RATE)."""
    steady = owned(words)
    return printed(words, wav, spots(steady)), printed(words, wav, glimpses(words, steady))
