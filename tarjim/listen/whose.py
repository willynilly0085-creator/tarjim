"""Each line's speaker, checked against the voice heard in it.

The cloud listener names speakers by what it hears, and it can swap them: on 2026-11-06 an
interview had host and guest swapped after a two-second pause, in all three listenings, so from
there on each one wore the other's colour. A long video's pieces have their labels linked to the
clip's names (listen/links.py, 2026-11-09), so the voices of the whole clip are compared
together. The labels are corrected, never invented: one speaker is never checked against nobody.

Since 2026-11-09 the voices are heard in windows of steady talk (listen/turns.py), grouped into
the clip's voices (listen/cluster.py), with each label split where its voice changes
(listen/changes.py) and each line given the voice of its part of the label
(listen/windowed.py): a swap inside one request is undone from the pause it began at, short
replies after it included, a listener's fake split joins, and a voice no label told apart gets
a speaker of its own, however many speakers that makes. When the voices found are not clearly
apart no line is moved and the log says why. A clip with too little steady talk for that (under
10 s of one of two voices) is checked line by line as before (listen/lined.py). A line the
listener gave no speaker (a fill heard on this computer) is never judged by its print; it takes
the nearer turn (speakers.inherited), after that turn's voice is put right.
"""
from dataclasses import replace
from typing import Any

from tarjim.asr.voiceprint import RATE
from tarjim.listen import lined
from tarjim.listen.follow import followed
from tarjim.listen.lined import FEWEST, MARGIN, STEADY, Labels, nearer, unreliable
from tarjim.listen.turns import windows
from tarjim.listen.windowed import Heard, decided
from tarjim.models import Word
from tarjim.speakers import inherited, linked_by_time, who

__all__ = ["FEWEST", "MARGIN", "STEADY", "by_voice", "checked", "followed", "nearer",
           "unreliable"]


def relabelled(words: list[Word], labels: Labels) -> tuple[list[Word], int]:
    """The words with each line given its speaker, and how many lines that moved."""
    out = list(words)
    moved = 0
    for (first, last), name in labels.items():
        if name != who(words[first].speaker):
            out[first:last] = [replace(w, speaker=name) for w in out[first:last]]
            moved += 1
    return out, moved


def heard_in(wav: Any, start: float, end: float) -> Any:
    """The voice print of the sound from start to end."""
    from tarjim.asr.voiceprint import print_of

    return print_of(wav[int(start * RATE):int(end * RATE)])


def checked(words: list[Word], wav: Any) -> list[Word]:
    """The words with each line given to the speaker whose voice it is: by the clip's windows
    of steady talk, or line by line where it has too little of it."""
    steady, glimpses = windows(words, wav)
    verdict = decided(words, Heard(steady, glimpses, lambda start, end: heard_in(wav, start, end)))
    if verdict.little:
        print(f"speakers: {verdict.why}; each line checked by its own voice", flush=True)
        return lined.checked(words, wav)
    if verdict.why:
        print(f"speakers: no line given to another speaker by voice: {verdict.why} "
              f"({verdict.note})", flush=True)
        return words
    out, moved = relabelled(words, verdict.labels)
    print(f"speakers: {verdict.note}; {len(verdict.labels)} lines checked by voice, {moved} "
          f"given to another speaker", flush=True)
    return out


def voiced(words: list[Word], wav: Any) -> list[Word]:
    """The checked words, or the words as they are when no voice print can be made here."""
    from tarjim.asr.voiceprint import fetched

    if len({who(w.speaker) for w in words if w.speaker}) < FEWEST or not fetched():
        return words
    try:
        return checked(words, wav)
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        print(f"speakers: the voice check did not run: {str(error)[:200]}", flush=True)
        return words


def by_voice(words: list[Word], wav: Any, rate: int = RATE) -> list[Word]:
    """The words checked by voice as far as can be done here (sound at RATE only), each line the
    vote could not link given a base speaker by time where the check did not (2026-11-08), then
    each line without a speaker given to the nearer turn (by then put right)."""
    return inherited(linked_by_time(voiced(words, wav) if rate == RATE else words))
