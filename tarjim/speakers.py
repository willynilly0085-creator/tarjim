"""Who is speaking, from the listener's labels. A label may carry the voting pass that found a line
("p2.S1", tarjim/listen/vote.py): that names the pass, not another person. Every piece of a long
video keeps the listener's own labels (listen/chunks.py, since 2026-10-31), so a label names one
speaker in the whole clip, and speakers are ranked by how much they talk in the whole clip: the
one who talks most is the main voice. Only a transcript saved before then has labels tagged by
piece ("c0.S1", "c1.S1"); those are still ranked within their piece, so the main voice of every
piece keeps the main colour and voice when such a job is made again.

A line the listener gave no speaker (a fill heard on this computer) is part of the turn it touches
within TOUCHING, the way a word cut off by a pause is. Since 2026-11-08 it takes that turn's
speaker; with no turn that close it stays without one, rather than being handed to anybody.
"""
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import replace

from tarjim.models import Word

PASS_TAG = re.compile(r"(?:^|(?<=\.))p\d+\.")
GAP = 1.0  # seconds of silence that end a line even with the same speaker
TOUCHING = 0.3  # seconds: a line without a speaker this close to a turn belongs to it

Line = tuple[int, int]  # the first word and the one past the last


def who(label: str) -> str:
    return PASS_TAG.sub("", label)


def ranked(words: Iterable[Word]) -> dict[str, int]:
    """Each speaker's place by talk in the whole clip (in their piece for an old "c0." label):
    0 for the one who talks most."""
    talk = Counter(who(w.speaker) for w in words if w.speaker)
    taken: Counter[str] = Counter()
    ranks: dict[str, int] = {}
    for name, _ in talk.most_common():
        piece = name.rpartition(".")[0]
        ranks[name], taken[piece] = taken[piece], taken[piece] + 1
    return ranks


def lines(words: list[Word]) -> list[Line]:
    """The words in lines: one speaker's words with no pause longer than GAP between them."""
    found: list[Line] = []
    for k, word in enumerate(words):
        if found and who(words[k - 1].speaker) == who(word.speaker) and (
                word.start - words[k - 1].end <= GAP):
            found[-1] = (found[-1][0], k + 1)
        else:
            found.append((k, k + 1))
    return found


def span(words: list[Word], line: Line) -> tuple[float, float]:
    return words[line[0]].start, words[line[1] - 1].end


def touching(words: list[Word], line: Line) -> str:
    """The speaker of the nearer turn within TOUCHING of a line, or "" when none is."""
    start, end = span(words, line)
    before = [(start - words[line[0] - 1].end, words[line[0] - 1].speaker)] if line[0] else []
    after = [(words[line[1]].start - end, words[line[1]].speaker)] if line[1] < len(words) else []
    near = [(gap, name) for gap, name in before + after if name and gap < TOUCHING]
    return min(near)[1] if near else ""


def inherited(words: list[Word]) -> list[Word]:
    """The words with each line that has no speaker given to the turn it touches."""
    out = list(words)
    for first, last in lines(words):
        name = "" if words[first].speaker else touching(words, (first, last))
        if name:
            out[first:last] = [replace(w, speaker=name) for w in out[first:last]]
    return out
