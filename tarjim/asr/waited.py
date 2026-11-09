"""Turns the in-order search made wait for the end of the turn they were said over (2026-11-08).

One search keeps every turn's letters after the last one's, so a turn begun over the end of
another was timed only once that one's letters ended: "That is far too simple." 0.55 s late and
"And what about students" 0.9 s late on every en_debate_overlap run, its subtitle up after its
first words. Such a turn is searched again on its own, only within TIGHT of the time the
listener gave it, so its words cannot go to the other voice's matching letters seconds away; the
new times are kept only when they start earlier. Searching it on its own from the first, outside
the one search, drew the turns after it seconds off toward the speech left without its words.

Only lines heard where they are timed take part (2026-11-09). A line the listener put a minute
late (an mm:ss misread inside its piece) lands in other speech, where its words are not said, and
searched alone it takes whatever letters lie in its window: it cut another line's subtitle short
(en_monologue: 14 words missed instead of 1; en_long_three_pieces), or was shown rushed over its
own speaker's question (en_long_seven); and the guest's answer said over such a line waited for
it, moved under it and showed its first words late (mixed_en_ar). The one search tells such a
line: it finds next to none of its words (0 to 2 of 10 or 11), while a turn really said over the
end of another goes on after it, where the one search finds its later words (6 of 14 or more
with the listener's words partly wrong), and the line it was said over is found there (4 of 9 or
more). So a line makes a turn wait, and a turn of more than SHORT words waits, only when the one
search found at least HEARD of its words; a share of words found by the search alone, or of
half, tried first, also stopped real overlaps whose words the listener got partly wrong
(en_debate_overlap wrong_words). A line read back from an mm:ss misread outside its piece
(listen/chunks.SLIPPED) has no time to trust and takes no part either; nor does a voice wait for
its own line, one voice not speaking over itself.
"""
from typing import NamedTuple

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
TRUSTED = 1.0  # the prior of a line timed as heard (listen/gemini_listen.Utterance)
HEARD = 1 / 3  # share of a line's words the one search found where it put them: said there
SHORT = 4  # words: a reply this short said over waits whole, none of it found (align.SHORT_REPLY)


class Under(NamedTuple):
    """The trusted line reaching furthest so far: where it ends, whose voice, whether the one
    search found it there."""
    end: float
    speaker: str
    heard: bool


NOTHING = Under(float("-inf"), "", False)


def waited(utterances: list[Utterance], said_over: list[bool],
           words: list[Word]) -> list[tuple[int, int]]:
    """The waited turns as (line index, index of its first word in words). Words are in line
    order, each line's as many as split_words gives; a short reply said over is not a turn."""
    found: list[tuple[int, int]] = []
    under, first = NOTHING, 0
    for index, (line, over) in enumerate(zip(utterances, said_over, strict=True)):
        mine = words[first:first + len(split_words(line.text))]
        if mine and not over and waits(line, under, mine):
            found.append((index, first))
        if not over and line.prior >= TRUSTED and line.end > under.end:
            under = Under(line.end, line.speaker, heard(mine))
        first += len(mine)
    return found


def waits(line: Utterance, under: Under, mine: list[Word]) -> bool:
    """Begun before the line under it ended, in another voice, over a line found there; trusted,
    found where the one search put it unless short, and timed late (2026-11-09)."""
    over = line.start < under.end and line.speaker != under.speaker and under.heard
    found = len(mine) <= SHORT or heard(mine)
    return over and found and line.prior >= TRUSTED and late(mine[0], line)


def late(word: Word, line: Utterance) -> bool:
    return word.start > line.start + LATE


def heard(words: list[Word]) -> bool:
    """At least HEARD of the words with letters to hear are found where they are timed
    (agree.FOUND); words with none say nothing."""
    scores = [w.score for w in words if w.score is not None]
    return not scores or sum(score >= FOUND for score in scores) >= HEARD * len(scores)
