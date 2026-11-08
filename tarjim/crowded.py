"""A short subtitle squeezed between two turns shares the screen with part of one (2026-11-08).

Before, "Right." between two of the guest's long sentences was held for rules.shortest, and
the guest's next subtitle came up 0.56 s after its first word, three times in every
en_interview_quick run. A whole turn too long to share the screen is now cut where a long block
is cut (breaks.best_split): its first words become the exchange's second part, or its last words
the first part, and the rest keeps a subtitle of its own. Only a one-part subtitle is cut or
joined this way and the result is always a two-part exchange, so each join leaves one subtitle
fewer that could be joined again and the solver always ends.
"""
from tarjim.breaks import best_split
from tarjim.dialogue import MAX_SPEAKERS, last_end, like
from tarjim.joins import Frame, joinable, joined, joined_parts
from tarjim.models import Cue, Word


def handed(cues: list[Cue], index: int, frame: Frame) -> int | None:
    """Joins the subtitle at index to the next turn's first words, else to the last turn's last
    words; says which subtitle to place next, or None when neither can be."""
    if index + 1 < len(cues):
        pair = with_head(cues[index], cues[index + 1], frame)
        if pair:
            cues[index:index + 2] = pair
            return index
    if index:
        pair = with_tail(cues[index - 1], cues[index], frame)
        if pair:
            cues[index - 1:index + 1] = pair
            return index - 1
    return None


def with_head(cue: Cue, turn: Cue, frame: Frame) -> list[Cue] | None:
    if not (one_part(cue) and one_part(turn)):
        return None
    words = turn.words
    fits = [k for k in range(1, len(words)) if exchange(cue, piece(turn, words[:k]), frame)]
    if not fits:
        return None
    at = best_split(words, fits)
    return [joined(cue, piece(turn, words[:at]), frame), piece(turn, words[at:])]


def with_tail(turn: Cue, cue: Cue, frame: Frame) -> list[Cue] | None:
    if not (one_part(cue) and one_part(turn)):
        return None
    words = turn.words
    fits = [k for k in range(1, len(words)) if exchange(piece(turn, words[k:]), cue, frame)]
    if not fits:
        return None
    at = best_split(words, fits)
    return [piece(turn, words[:at]), joined(piece(turn, words[at:]), cue, frame)]


def exchange(first: Cue, second: Cue, frame: Frame) -> bool:
    return joinable(first, second, frame) and len(joined_parts(first, second, frame)) == \
        MAX_SPEAKERS


def one_part(cue: Cue) -> bool:
    return bool(cue.words) and not cue.text and len(cue.parts) <= 1


def piece(turn: Cue, words: list[Word]) -> Cue:
    """Some of a one-part subtitle's words as a subtitle of their own, a reply part kept one."""
    part = turn.parts[0] if turn.parts else turn.words
    start = turn.start if words[0] is turn.words[0] else min(w.start for w in words)
    return Cue(start, last_end(words), list(words), parts=[like(part, words)])
