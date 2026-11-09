"""A waited turn's own search that took another turn's same words (2026-11-09).

The listener's time for a turn can be seconds off too, and its own search then finds the same
words in the other voice's turn: a reply "Thank you." put over the host's "Thank you so much for
joining us." took the host's "Thank you", 2 s early (the bench's en_interview_music, 2026-11-09).
New times that put a word where another turn's same word is timed are not kept (echoes), when
the first search found the turn's letters where it waited (THERE): then there are two sounds,
and the other one is the turn's. Two voices can say the same words at once, too ("Common sense?"
with the other's "common sense.", the bench's en_debate_overlap, 2026-11-09): the letters are
there once, the first search found none of the turn's where it waited, and refusing the one
sound of both showed the reply 0.9 s late on silence.

Moved out of asr/waited.py on 2026-11-09, when the guard against a loop's copy (heard_there,
cleared) joined it there; asr/waited.py still offers these names.
"""
from tarjim.listen.vote import norm
from tarjim.models import Word

# The mean likelihood of a turn's letters where the first search timed it under which none were
# there (2026-11-09): 0.00 for a reply said with the other voice's same words, 0.25 to 0.28 for
# one said after them under a music bed (asr/agree.FOUND, 0.3, is a run surely said).
THERE = 0.1


def echoes(alone: list[Word], words: list[Word], first: int) -> bool:
    """Whether the turn's own search put one of its words on the time of the same word of
    another turn, while its letters were found where it waited: the other voice's, not its own."""
    if not found_there(words[first:first + len(alone)]):
        return False  # one sound of both voices: the turn's as much as the other's
    others = [*words[:first], *words[first + len(alone):]]
    return any(echo(a, o) for a in alone for o in others)


def found_there(words: list[Word]) -> bool:
    """Whether the first search found the turn's letters where it timed it (no scores: as if)."""
    scores = [w.score for w in words if w.score is not None]
    return not scores or sum(scores) / len(scores) >= THERE


def echo(one: Word, other: Word) -> bool:
    """Two words of one text timed over each other: one sound, so one of them is not there."""
    return norm(one.text) == norm(other.text) and one.start < other.end and other.start < one.end
