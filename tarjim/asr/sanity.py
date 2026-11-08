"""Whether heard words are timed the way people speak, so a broken timing never reaches the
subtitles.

On 2026-10-30 a 2-minute speech came out with all 378 words inside 5 seconds: one listening pass
had returned the whole speech as a single 129-second line, the vote built its time from it, and
every subtitle flashed for a few hundredths of a second at 1:05, so the video looked untranslated.
People say at most about 6 words a second; a timing far past that is wrong, whatever made it.
"""
from collections.abc import Iterable

from tarjim import guards
from tarjim.models import Word
from tarjim.scripts import UNSPACED, split_words

FASTEST = 8.0  # words a second over the whole speech, well past anyone's real rate
SHORTEST = 0.02  # seconds: a word this short was squeezed, not said
SQUEEZED = 0.3  # share of such words that marks the timing as broken
LONGEST_LINE = 60.0  # seconds: no listener's single line is longer
FEWEST = 10  # words: fewer say nothing
# A character of a script written without spaces counts as a quarter of a word: a Chinese or
# Japanese character is a syllable, and Thai splits one syllable into about three pieces, so a
# fast Thai speaker says some 20 of them a second (2026-11-08).
UNSPACED_WORD = 0.25


def counted(units: Iterable[str]) -> float:
    """Words, the way scripts.split_words splits them, with unspaced pieces weighed as above."""
    return sum(UNSPACED_WORD if UNSPACED.search(unit) else 1.0 for unit in units)


def rate(words: list[Word]) -> float:
    span = words[-1].end - words[0].start
    return counted(w.text for w in words) / span if span > 0 else float("inf")


def implausible(words: list[Word]) -> bool:
    if len(words) < FEWEST:
        return False
    squeezed = sum(w.end - w.start < SHORTEST for w in words) / len(words)
    return guards.when("sanity.implausible", squeezed > SQUEEZED or rate(words) > FASTEST)


def plausible_line(start: float, end: float, text: str) -> bool:
    """One listener line: no longer than anyone speaks in one go, no faster than anyone talks.
    Counted on spaces alone (until 2026-11-08), a whole Japanese speech in one line was one word."""
    seconds, count = end - start, counted(split_words(text))
    return seconds <= LONGEST_LINE and (count < FEWEST or count <= FASTEST * max(seconds, 0.1))
