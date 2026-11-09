"""Each line's speaker, checked against the voice heard in it.

The cloud listener names speakers by what it hears, and it can swap them: on 2026-11-06 an
interview had host and guest swapped after a two-second pause, in all three listenings, so from
there on each one wore the other's colour. Here every line long enough to know a voice by gets a
voice print (asr/voiceprint.py), and a line whose voice is clearly another speaker's, by MARGIN or
more, is given to that speaker. A long video's pieces have their labels linked to the clip's names
(listen/links.py, 2026-11-09), so the voices of the whole clip are compared together. The labels are
corrected, never invented: one speaker is never checked against nobody.

Since 2026-11-08 a line is judged against averages that leave it out. With the line inside its own
speaker's average, a swap from some point on made both averages a mix of both voices, and a
swapped line was almost never clearly nearer the other one. Judging is done again on the labels
each round leaves, until no line moves (ROUNDS at most), so the lines already in place pull each
average back to one voice. Leaving the line out also took away the pull of its own label, so
when the voices that come out are not clearly two people, no line is moved and the log says why:
averages all over SAME alike, or lines on average not APART nearer their own speaker than another
(one voice under two labels, singing, a voice changed by effects). A line too short to know a
voice by is not judged by its print; it goes where its label's long lines went (listen/follow.py).
A line the listener gave no speaker (a fill heard on this computer) is never judged by its print
either; it takes the nearer turn (speakers.inherited), after that turn's voice is put right.
"""
from dataclasses import dataclass, replace
from itertools import combinations
from typing import Any, NamedTuple

import numpy as np

from tarjim.asr.voiceprint import RATE
from tarjim.listen.follow import NEAREST, adopted, followed
from tarjim.models import Word
from tarjim.speakers import Line, inherited, lines, linked_by_time, span, who

SHORTEST = 0.8  # seconds: a shorter line says too little to know the voice by
STEADY = 1.5  # seconds: lines this long make up a speaker's average print
MARGIN = 0.15  # how much closer another speaker's voice must be to take the line
FEWEST = 2  # speakers: one is never checked against nobody
ROUNDS = 5  # times the lines are judged again on the labels the last round left
SAME = 0.8  # averages all this alike are one voice under two labels, not two people
APART = 0.2  # lines must sit at least this much nearer their own speaker, on average

Labels = dict[Line, str]


@dataclass(frozen=True)
class Prints:
    """The voice print of each line long enough to know a voice by, and which lines are steady."""

    voices: dict[Line, np.ndarray]
    steady: frozenset[Line]


class Sum(NamedTuple):
    """One speaker's prints added up, over all their lines and over their steady ones."""

    every: np.ndarray
    lines: int
    calm: np.ndarray
    calm_lines: int

    def direction(self) -> np.ndarray | None:
        """Where the speaker's average points: their steady lines, or all when none is."""
        return self.calm if self.calm_lines else self.every if self.lines else None

    def without(self, voice: np.ndarray, steady: bool) -> np.ndarray | None:
        """Where the average points with one of the speaker's lines taken out of it."""
        calm = Sum(self.every, self.lines, self.calm - voice, self.calm_lines - 1)
        rest = calm if steady else self
        return Sum(rest.every - voice, rest.lines - 1, rest.calm, rest.calm_lines).direction()


def cosine(one: np.ndarray, other: np.ndarray) -> float:
    size = float(np.linalg.norm(one) * np.linalg.norm(other))
    return float(one @ other) / size if size > 0 else 0.0


def sums(prints: Prints, labels: Labels) -> dict[str, Sum]:
    found: dict[str, Sum] = {}
    for line, voice in prints.voices.items():
        nothing = np.zeros_like(voice)
        old = found.get(labels[line], Sum(nothing, 0, nothing, 0))
        calm = int(line in prints.steady)
        found[labels[line]] = Sum(old.every + voice, old.lines + 1, old.calm + calm * voice,
                                  old.calm_lines + calm)
    return found


def averages(prints: Prints, labels: Labels) -> dict[str, np.ndarray]:
    """Each speaker's print over their steady lines, or over all their lines when none is."""
    found = {name: total.direction() for name, total in sums(prints, labels).items()}
    return {name: voice for name, voice in found.items() if voice is not None}


def nearer(voice: np.ndarray, own: str, known: dict[str, np.ndarray]) -> str:
    """Another speaker whose voice this clearly is, or own; own too when own has no other line."""
    if own not in known or len(known) < FEWEST:
        return own
    alike = {name: cosine(voice, average) for name, average in known.items()}
    best = max(alike, key=alike.__getitem__)
    return best if alike[best] >= NEAREST and alike[best] - alike[own] >= MARGIN else own


def judged(prints: Prints, labels: Labels, pool: dict[str, Sum], line: Line) -> str:
    """Whose voice the line is, against every speaker's average without the line in it."""
    voice, own = prints.voices[line], labels[line]
    known = {name: total.without(voice, line in prints.steady) if name == own
             else total.direction() for name, total in pool.items()}
    return nearer(voice, own, {name: v for name, v in known.items() if v is not None})


def refined(prints: Prints, labels: Labels) -> Labels:
    """The labels judged again on the labels each round leaves, until no line moves."""
    for _ in range(ROUNDS):
        pool = sums(prints, labels)
        moved = {line: judged(prints, labels, pool, line) for line in labels}
        if moved == labels:
            break
        labels = moved
    return labels


def apart(prints: Prints, labels: Labels) -> float:
    """How much nearer each line is, on average, to its own speaker (without it) than to another:
    about 0.3 or more for two people, near 0 for one voice under two labels."""
    pool, known = sums(prints, labels), averages(prints, labels)
    found = []
    for line, voice in prints.voices.items():
        mine = pool[labels[line]].without(voice, line in prints.steady)
        rivals = [cosine(voice, v) for name, v in known.items() if name != labels[line]]
        if mine is not None and rivals:
            found.append(cosine(voice, mine) - max(rivals))
    return float(np.mean(found)) if found else 0.0


def unreliable(prints: Prints, labels: Labels) -> str:
    """Why the voices in this clip cannot be told apart, or "" when they can."""
    known = averages(prints, labels)
    if len(known) < FEWEST:
        return "every line sounds like one voice"
    if all(cosine(one, other) > SAME for one, other in combinations(known.values(), 2)):
        return f"the speakers' voices are too alike (over {SAME}) to be told apart"
    if apart(prints, labels) < APART:
        return f"the lines are not clearly nearer their own speaker's voice (by {APART})"
    return ""


def printed(words: list[Word], wav: Any) -> Prints:
    from tarjim.asr.voiceprint import print_of

    found = {}
    for line in lines(words):
        start, end = span(words, line)
        if end - start >= SHORTEST and words[line[0]].speaker:
            found[line] = print_of(wav[int(start * RATE):int(end * RATE)])
    ends = {line: span(words, line) for line in found}
    return Prints(found, frozenset(line for line, (start, end) in ends.items()
                                   if end - start >= STEADY))


def checked(words: list[Word], wav: Any) -> list[Word]:
    """The words with each line given to the speaker whose voice it is."""
    prints = printed(words, wav)
    heard = {line: who(words[line[0]].speaker) for line in prints.voices}
    if len(averages(prints, heard)) < FEWEST:
        return words
    # 2026-11-08: unlinked "S2~p3" by voice first, a voice near no base speaker's its own speaker
    names = adopted(averages(prints, heard), {who(w.speaker) for w in words if w.speaker})
    labels = refined(prints, {line: names.get(name, name) for line, name in heard.items()})
    why = unreliable(prints, labels)
    if why:
        print(f"speakers: no line given to another speaker by voice: {why}", flush=True)
        return words
    out = list(words)
    moved = {line: name for line, name in labels.items() if name != heard[line]}
    short = followed(words, heard, labels)
    for (first, last), name in (moved | short).items():
        out[first:last] = [replace(w, speaker=name) for w in out[first:last]]
    print(f"speakers: {len(labels)} lines checked by voice, {len(moved)} given to another "
          f"speaker, {len(short)} short lines with them", flush=True)
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
