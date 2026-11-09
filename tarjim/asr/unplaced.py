"""Words the tolerant aligner left out (asr/tolerated.py): text the sound does not hold where it
is timed (2026-11-09). Before, every written word was squeezed onto the sound, so a line the
listener wrote twice, or one it made up, took the time of the speech beside it and pushed that
speech's words off their voice. Each run of one line's words left out is, in order:

1. a copy, when it is most of its line (SIMILAR of the line's words or more: a listener writes
   a whole line twice, while a word the skip left out of a line said is a word missed) and
   SIMILAR of its words are said by words placed within NEAR seconds of its line (vote.norm):
   dropped, the listener wrote it twice (a Gemini loop too). Before 2026-11-09's bench a lone
   "The" left out of a line said was dropped as a copy of another "the" close by;
2. otherwise spread over the speech inside its own room in its line (piles.spread), between
   the line's words placed around it, and marked estimated;
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
    """The words by their start, so those around a line are found without reading them all."""

    def __init__(self, words: list[Word]) -> None:
        self.order = sorted(range(len(words)), key=lambda i: words[i].start)
        self.starts = [words[i].start for i in self.order]

    def around(self, line: Utterance, besides: set[int]) -> list[int]:
        """The words starting within NEAR seconds of the line, less `besides`, in order."""
        first = bisect_left(self.starts, line.start - NEAR)
        past = bisect_right(self.starts, line.end + NEAR)
        return sorted(i for i in self.order[first:past] if i not in besides)


def copied(words: list[Word], piece: list[int], nearby: list[int]) -> bool:
    """60% or more of the piece's words said, in order, by the words nearby."""
    mine = [n for n in (norm(words[i].text) for i in piece) if n]
    near = [norm(words[i].text) for i in nearby]
    blocks = SequenceMatcher(None, mine, near, autojunk=False).get_matching_blocks()
    return bool(mine) and sum(b.size for b in blocks) >= SIMILAR * len(mine)


def a_copy(words: list[Word], piece: list[int], lines: Lines, left: set[int]) -> bool:
    """Most of its line, and a copy of words placed close by (rule 1)."""
    owner = owners(lines.utterances)
    line = lines.utterances[owner[piece[0]]]
    most = len(piece) >= SIMILAR * len(split_words(line.text))
    return most and copied(words, piece, Near(words).around(line, left))


def all_copies(words: list[Word], left: set[int], lines: Lines) -> bool:
    """Every run of `left` a copy of words placed close by."""
    return all(a_copy(words, piece, lines, left)
               for piece in pieces(left, owners(lines.utterances)))


def room(words: list[Word], piece: list[int], owner: list[int], line: Utterance) -> Span:
    """The line's time between its words placed before and after the run."""
    before, after = piece[0] - 1, piece[-1] + 1
    start = words[before].end if before >= 0 and owner[before] == owner[piece[0]] else line.start
    end = words[after].start if after < len(words) and owner[after] == owner[piece[0]] \
        else line.end
    return (start, end) if end > start else (line.start, line.end)


def settled(words: list[Word], left: set[int], lines: Lines) -> Outcome:
    """The words with each run left out dropped as a copy or spread and marked."""
    from tarjim.asr.piles import spread

    owner, outcome = owners(lines.utterances), Outcome(list(words))
    if len(owner) != len(words):
        return outcome
    for piece in pieces(left, owner):
        line = lines.utterances[owner[piece[0]]]
        if a_copy(words, piece, lines, left):
            outcome.dropped |= set(piece)
            continue
        placed = spread([words[i] for i in piece], room(words, piece, owner, line), lines.speech)
        outcome.words[piece[0]:piece[-1] + 1] = placed
        outcome.regions.append(Region(placed[0].start, placed[-1].end, "unplaced"))
    told(outcome, len(left))
    return outcome


def told(outcome: Outcome, left: int) -> None:
    guards.fired("unplaced.duplicate", len(outcome.dropped))
    guards.fired("unplaced.estimated", left - len(outcome.dropped))
    if left:
        print(f"aligner: {left} words not found in the sound where they are timed: "
              f"{len(outcome.dropped)} written twice dropped, "
              f"{left - len(outcome.dropped)} spread over their line in "
              f"{len(outcome.regions)} stretch(es)", flush=True)
