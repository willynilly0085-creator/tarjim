"""Turns the in-order search made wait for the end of the turn they were said over (2026-11-08).

One search keeps every turn's letters after the last one's, so a turn begun over the end of
another was timed only once that one's letters ended: "That is far too simple." 0.55 s late and
"And what about students" 0.9 s late on every en_debate_overlap run, its subtitle up after its
first words. Such a turn is searched again on its own, only within TIGHT of the time the
listener gave it, so its words cannot go to the other voice's matching letters seconds away; the
new times are kept only when they start earlier. Searching it on its own from the first, outside
the one search, drew the turns after it seconds off toward the speech left without its words.

The listener's time for a turn can be seconds off too, and its own search then finds the same
words in the other voice's turn: a reply "Thank you." put over the host's "Thank you so much for
joining us." took the host's "Thank you", 2 s early (the bench's en_interview_music, 2026-11-09).
New times that put a word where another turn's same word is timed are not kept (echoes).
"""
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

# Timed this much after the listener said it began, a turn waited for another one's letters. The
# listener's own times can be off by 0.3 s (the bench's jitter), so a turn 0.3 s late may just be
# a listener's early start: before, an Arabic one-word reply timed 0.32 s after it was moved
# 0.3 s before it was said.
LATE = 0.4
TIGHT = 0.3  # seconds either side of its own time a waited turn is searched in again


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


def echoes(alone: list[Word], words: list[Word], first: int) -> bool:
    """Whether the turn's own search put one of its words on the time of the same word of
    another turn: the other voice's letters, not its own."""
    others = [*words[:first], *words[first + len(alone):]]
    return any(echo(a, o) for a in alone for o in others)


def echo(one: Word, other: Word) -> bool:
    """Two words of one text timed over each other: one sound, so one of them is not there."""
    return norm(one.text) == norm(other.text) and one.start < other.end and other.start < one.end
