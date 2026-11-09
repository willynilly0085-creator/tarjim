"""Turns the in-order search made wait for the end of the turn they were said over (2026-11-08).

One search keeps every turn's letters after the last one's, so a turn begun over the end of
another was timed only once that one's letters ended: "That is far too simple." 0.55 s late and
"And what about students" 0.9 s late on every en_debate_overlap run, its subtitle up after its
first words. Such a turn is searched again on its own, only within TIGHT of the time the
listener gave it, so its words cannot go to the other voice's matching letters seconds away; the
new times are kept only when they start earlier. Searching it on its own from the first, outside
the one search, drew the turns after it seconds off toward the speech left without its words.

A turn found starting well past the heard end of the turn it seems said over did not wait for
that one's letters (2026-11-09): the listener's times are off there, as when a whole piece is
heard 3 s early (the bench's early fault), and its own time holds other speech. Searched again
there it took the host's letters: en_interview_music's "Today my guest" 2.5 s early and
en_long_seven's "Have you ever thought" 2.2 s early, their words then missing and said twice.
"""
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import split_words

# Timed this much after the listener said it began, a turn waited for another one's letters. The
# listener's own times can be off by 0.3 s (the bench's jitter), so a turn 0.3 s late may just be
# a listener's early start: before, an Arabic one-word reply timed 0.32 s after it was moved
# 0.3 s before it was said.
LATE = 0.4
TIGHT = 0.3  # seconds either side of its own time a waited turn is searched in again
# Found starting this long after the heard end of the turn it was said over, it did not wait for
# it (2026-11-09): waited turns on en_debate_overlap start within 0.4 s of it, the turns of a
# piece heard 3 s early 1.8 s and more past it.
PAST = 1.0


def waited(utterances: list[Utterance], said_over: list[bool],
           words: list[Word]) -> list[tuple[int, int]]:
    """The waited turns as (line index, index of its first word in words). Words are in line
    order, each line's as many as split_words gives; a short reply said over is not a turn."""
    found: list[tuple[int, int]] = []
    reach, first = float("-inf"), 0
    for index, (line, over) in enumerate(zip(utterances, said_over, strict=True)):
        size = len(split_words(line.text))
        if size and not over and line.start < reach and late(words[first], line, reach):
            found.append((index, first))
        first += size
        reach = reach if over else max(reach, line.end)
    return found


def late(word: Word, line: Utterance, reach: float) -> bool:
    """Late after its own start, yet not past the other turn's heard end (2026-11-09)."""
    return line.start + LATE < word.start <= reach + PAST
