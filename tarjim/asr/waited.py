"""Turns the in-order search made wait for the end of the turn they were said over (2026-11-08).

One search keeps every turn's letters after the last one's, so a turn begun over the end of
another was timed only once that one's letters ended: "That is far too simple." 0.55 s late and
"And what about students" 0.9 s late on every en_debate_overlap run, its subtitle up after its
first words. Such a turn is searched again on its own, only within TIGHT of the time the
listener gave it, so its words cannot go to the other voice's matching letters seconds away; the
new times are kept only when they start earlier. Searching it on its own from the first, outside
the one search, drew the turns after it seconds off toward the speech left without its words.

Since 2026-11-09 they are kept only where its letters are heard (HEARD). A search inside a short
stretch always puts the letters somewhere, and a line the listener heard again (a loop) or moved
off its speech (the local words of a repeated line) was laid over the end of the turn before it
on letters that are not its own: "Those trials were run in office jobs." over "on four days",
"Can I bring my dog?" over "on the bus this time", each turn's subtitle cut short for the copy.
And a turn whose own search runs on over the next line's words where they are not heard (RAN
OVER) is searched again only up to that line's start: the one search had put a copy of a looped
line on the end of mixed_en_ar's Arabic reply, and the reply searched alone ran 1 s over it, both
shown in one dialogue subtitle cut to 0.9 s. Over words heard there, two voices said at once
(the debate's "They can use the school" under "And what about students"), its times stay.
"""
from dataclasses import replace
from itertools import takewhile
from statistics import mean

from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import split_words

# Timed this much after the listener said it began, a turn waited for another one's letters. The
# listener's own times can be off by 0.3 s (the bench's jitter), so a turn 0.3 s late may just be
# a listener's early start: before, an Arabic one-word reply timed 0.32 s after it was moved
# 0.3 s before it was said.
LATE = 0.4
TIGHT = 0.3  # seconds either side of its own time a waited turn is searched in again
# The mean likelihood of its words' letters at which a waited turn searched again is said there.
# On the bench (2026-11-09) the debate's turns said over another's end scored 0.59 to 0.88 and
# real turns begun over a looped line 0.84 and 0.92; lines heard again where they were not
# said scored 0.19 to 0.42, the letters of the speech under them taken for theirs.
HEARD = 0.5
EVEN = 1e-6  # seconds: times from two searches that meet at one frame differ by this much


def waited(utterances: list[Utterance], said_over: list[bool],
           words: list[Word]) -> list[tuple[int, int]]:
    """The waited turns as (line index, index of its first word in words). Words are in line
    order, each line's as many as split_words gives; a short reply said over is not a turn."""
    found: list[tuple[int, int]] = []
    reach, first = float("-inf"), 0
    for index, (line, over) in enumerate(zip(utterances, said_over, strict=True)):
        size = len(split_words(line.text))
        if size and not over and line.start < reach and late(words[first], line):
            found.append((index, first))
        first += size
        reach = reach if over else max(reach, line.end)
    return found


def late(word: Word, line: Utterance) -> bool:
    return word.start > line.start + LATE


def heard_there(words: list[Word]) -> bool:
    """Whether a turn searched again is said where the search put it: its letters are heard
    there (2026-11-09). Words with no letters to hear say nothing either way."""
    scores = [w.score for w in words if w.score is not None]
    return bool(scores) and mean(scores) >= HEARD


def unheard(words: list[Word]) -> bool:
    """Words whose letters are heard little where they are timed (2026-11-09); words with no
    letters to hear say nothing either way."""
    scores = [w.score for w in words if w.score is not None]
    return bool(scores) and mean(scores) < HEARD


def ran_over(turn: list[Word], after: list[Word]) -> list[Word]:
    """The words after a turn searched again that begin before its new end (2026-11-09)."""
    return list(takewhile(lambda w: w.start < turn[-1].end - EVEN, after))


def before(line: Utterance, at: float) -> Utterance | None:
    """The line searched again ending at `at`, its own search reaching TIGHT past its end; None
    when nothing of its own time is left (2026-11-09)."""
    end = min(line.end, at - TIGHT)
    return replace(line, end=end) if end > line.start else None
