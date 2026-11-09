"""Turns the in-order search made wait for the end of the turn they were said over (2026-11-08).

One search keeps every turn's letters after the last one's, so a turn begun over the end of
another was timed only once that one's letters ended: "That is far too simple." 0.55 s late and
"And what about students" 0.9 s late on every en_debate_overlap run, its subtitle up after its
first words. Such a turn is searched again on its own, only within TIGHT of the time the
listener gave it, so its words cannot go to the other voice's matching letters seconds away; the
new times are kept only when they start earlier. Searching it on its own from the first, outside
the one search, drew the turns after it seconds off toward the speech left without its words.

The new times are kept only when most of the turn's words are found where they land (2026-11-09):
a line the listener put a minute late fell inside another line, where its words are not said, and
searched alone it took that line's letters (4 of its 10 words found there), cutting that line's
subtitle short under it. A turn really said over another's end is found there: 4 of 5 words for
"That is far too simple.", both for the echoed "Common sense?", a slipped line 3 or 4 of 10 or 11.
"""
from tarjim.asr.agree import FOUND
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import split_words

# Timed this much after the listener said it began, a turn waited for another one's letters. The
# listener's own times can be off by 0.3 s (the bench's jitter), so a turn 0.3 s late may just be
# a listener's early start: before, an Arabic one-word reply timed 0.32 s after it was moved
# 0.3 s before it was said.
LATE = 0.4
TIGHT = 0.3  # seconds either side of its own time a waited turn is searched in again
MOST = 0.5  # share of a turn's words found where its own search puts them, to move it there


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
    """Most of the words whose letters were heard are found where they are timed (agree.FOUND);
    words with no letters to hear say nothing."""
    scores = [w.score for w in words if w.score is not None]
    return not scores or sum(score >= FOUND for score in scores) > MOST * len(scores)
