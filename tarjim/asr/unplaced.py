"""Words the tolerant aligner left out (asr/tolerated.py): text the sound does not hold where it
is timed (2026-11-09). Before, every written word was squeezed onto the sound, so a line the
listener wrote twice, or one it made up, took the time of the speech beside it and pushed that
speech's words off their voice. Each line with words left out is, in order:

1. a copy, when most of it is left out (SIMILAR of the line's words or more: a listener writes
   a whole line twice, while a word the skip left out of a line said is a word missed) and
   SIMILAR of those words are said by its own speaker's words placed within NEAR seconds of
   it (vote.norm): dropped whole, the listener wrote it twice (a Gemini loop too). Before
   2026-11-09's bench a lone "The" left out of a line said was dropped as a copy of another
   "the" close by;
2. otherwise each run of it left out is spread over the speech inside its own room in the line
   (piles.spread), between the line's words placed around it, less the speech other words were
   found on, and marked estimated; with less than HEARD_LEAST seconds of it a word, it is not
   shown (an invented line over silence or over another line's speech);
3. and its stretch given back as a Region of kind 'unplaced', for a later step to ask about.
"""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import NamedTuple

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

SIMILAR = 0.6  # of the run's words said nearby: a copy
NEAR = 8.0  # seconds around its line those words are looked for in
HEARD_LEAST = 0.1  # seconds of free speech a word left out needs to be spread (2026-11-09)

Span = tuple[float, float]


class Region(NamedTuple):
    start: float
    end: float
    kind: str


@dataclass(frozen=True)
class Lines:
    """The lines the words were aligned from, in their order, and the speech in their sound."""
    utterances: list[Utterance]
    speech: list[Span]


@dataclass
class Outcome:
    words: list[Word]
    dropped: set[int] = field(default_factory=set)  # indices of the copies
    regions: list[Region] = field(default_factory=list)
    estimated: int = 0  # words spread
    unheard: set[int] = field(default_factory=set)  # too little free speech: not shown


def owners(utterances: list[Utterance]) -> list[int]:
    """Each word's line, as asr/align.AlignEngine.align gives them."""
    return [k for k, u in enumerate(utterances) for _ in split_words(u.text)]


def pieces(left: set[int], owner: list[int]) -> list[list[int]]:
    """The words left out, in runs of one line's words one after another."""
    found: list[list[int]] = []
    for index in sorted(left):
        last = found[-1][-1] if found else -2
        if last == index - 1 and owner[last] == owner[index]:
            found[-1].append(index)
        else:
            found.append([index])
    return found


class Near:
    """The words by their start, so those around a line are found without reading them all, and
    the lines they were aligned from."""

    def __init__(self, words: list[Word], lines: list[Utterance]) -> None:
        self.words, self.lines, self.owner = words, lines, owners(lines)
        self.order = sorted(range(len(words)), key=lambda i: words[i].start)
        self.starts = [words[i].start for i in self.order]

    def around(self, line: Utterance, besides: set[int]) -> list[int]:
        """The words starting within NEAR seconds of the line, less `besides`, in order."""
        first = bisect_left(self.starts, line.start - NEAR)
        past = bisect_right(self.starts, line.end + NEAR)
        return sorted(i for i in self.order[first:past] if i not in besides)

    def voiced(self, index: int, other: int) -> bool:
        """Word `other` may be said by word `index`'s speaker: the same label, or labels that do
        not compare, of two requests (a line asked again comes back as "S2~x1386")."""
        mine, theirs = self.lines[self.owner[index]], self.lines[self.owner[other]]
        same = self.words[index].speaker == self.words[other].speaker
        return same or not mine.request or mine.request != theirs.request

    def copied(self, piece: list[int], besides: set[int]) -> bool:
        """60% or more of the piece's words said, in order, by its own speaker's words near its
        line, less `besides`: a listener's loop repeats one speaker's line, and another speaker
        saying the same words is a line of its own (the review of 2026-11-09, en_refrain_twice x
        loop_all)."""
        line = self.lines[self.owner[piece[0]]]
        nearby = [i for i in self.around(line, besides) if self.voiced(piece[0], i)]
        mine = [n for n in (norm(self.words[i].text) for i in piece) if n]
        near = [norm(self.words[i].text) for i in nearby]
        blocks = SequenceMatcher(None, mine, near, autojunk=False).get_matching_blocks()
        return bool(mine) and sum(b.size for b in blocks) >= SIMILAR * len(mine)


def by_line(left: set[int], owner: list[int]) -> dict[int, list[int]]:
    """The words left out, by their line, in order."""
    found: dict[int, list[int]] = {}
    for index in sorted(left):
        found.setdefault(owner[index], []).append(index)
    return found


def a_copy(words: list[Word], line: int, lines: Lines, left: set[int]) -> bool:
    """Most of the line left out, and that a copy of its speaker's words placed close by, the
    line's own words still placed not among them (rule 1). Judged on the line, not on each
    run of it: the skip may place a short word of a copy ("at") on a stray frame, which cut
    the copy into runs too short to be one (the bench, 2026-11-09). Left out are the words in
    `left` and those an earlier window's reading marked unplaced."""
    owner = owners(lines.utterances)
    mine = [i for i, k in enumerate(owner) if k == line]
    gone = [i for i in mine if i in left or words[i].source == "unplaced"]
    most = bool(gone) and len(gone) >= SIMILAR * len(mine)
    return most and Near(words, lines.utterances).copied(gone, left | set(mine))


def all_copies(words: list[Word], left: set[int], lines: Lines) -> bool:
    """Every line with words in `left` a copy of words placed close by."""
    return all(a_copy(words, line, lines, left)
               for line in by_line(left, owners(lines.utterances)))


def room(words: list[Word], piece: list[int], owner: list[int], line: Utterance) -> Span:
    """The line's time between its words placed before and after the run."""
    before, after = piece[0] - 1, piece[-1] + 1
    start = words[before].end if before >= 0 and owner[before] == owner[piece[0]] else line.start
    end = words[after].start if after < len(words) and owner[after] == owner[piece[0]] \
        else line.end
    return (start, end) if end > start else (line.start, line.end)


def settled(words: list[Word], left: set[int], lines: Lines) -> Outcome:
    """The words with each line left out dropped as a copy, or its runs spread and marked."""
    from tarjim.asr.alike import first_written

    owner, outcome = owners(lines.utterances), Outcome(list(words))
    if len(owner) != len(words):
        return outcome
    for line, gone in by_line(left, owner).items():
        if a_copy(words, line, lines, left):
            outcome.dropped |= {i for i, k in enumerate(owner) if k == line}
            continue
        for piece in pieces(set(gone), owner):
            spread_out(outcome, piece, Lines([lines.utterances[line]], lines.speech), owner)
    outcome.dropped = first_written(outcome.words, outcome.dropped, lines.utterances, owner)
    told(outcome, len(left))
    return outcome


def spread_out(outcome: Outcome, piece: list[int], line: Lines, owner: list[int]) -> None:
    """A run left out spread over the free speech in its room, marked, and its stretch kept
    (rules 2 and 3); with too little for its words, not shown (Outcome.unheard)."""
    from tarjim.asr.piles import spread

    words = outcome.words
    room_of = room(words, piece, owner, line.utterances[0])
    speech = free_in(outcome, piece, room_of, line.speech)
    if line.speech and sum(b - a for a, b in speech) < HEARD_LEAST * len(piece):
        outcome.unheard |= set(piece)
        outcome.regions.append(Region(*room_of, "unplaced"))
        return
    placed = spread([words[i] for i in piece], room_of, speech)
    words[piece[0]:piece[-1] + 1] = placed
    outcome.estimated += len(placed)
    outcome.regions.append(Region(placed[0].start, placed[-1].end, "unplaced"))


def free_in(outcome: Outcome, piece: list[int], room_of: Span, speech: list[Span]) -> list[Span]:
    """The speech in the room that no other word placed was found on."""
    from tarjim.asr.spread import free
    taken = [(w.start, w.end) for i, w in enumerate(outcome.words)
             if w.source != "unplaced" and i not in outcome.dropped
             and not piece[0] <= i <= piece[-1] and w.end > room_of[0] and w.start < room_of[1]]
    return free(speech, room_of, taken)


def told(outcome: Outcome, left: int) -> None:
    guards.fired("unplaced.duplicate", len(outcome.dropped))
    guards.fired("unplaced.estimated", outcome.estimated)
    guards.fired("unplaced.unheard", len(outcome.unheard))
    if left:
        print(f"aligner: {left} words not found in the sound where they are timed: "
              f"{len(outcome.dropped)} of lines written twice dropped, "
              f"{outcome.estimated} spread over their line, {len(outcome.unheard)} with no free "
              f"speech there not shown; {len(outcome.regions)} stretch(es) to ask about",
              flush=True)
