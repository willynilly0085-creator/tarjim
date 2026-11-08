"""Who is speaking, from the listener's labels. A label may carry the voting pass that found a line
("p2.S1", tarjim/listen/vote.py): that names the pass, not another person. Every piece of a long
video keeps the listener's own labels (listen/chunks.py, since 2026-10-31), so a label names one
speaker in the whole clip, and speakers are ranked by how much they talk in the whole clip: the
one who talks most is the main voice. Only a transcript saved before then has labels tagged by
piece ("c0.S1", "c1.S1"); those are still ranked within their piece, so the main voice of every
piece keeps the main colour and voice when such a job is made again.

A line the listener gave no speaker (a fill heard on this computer) was drawn in the main voice's
colour, whoever said it. Since 2026-11-08 it takes the speaker of the nearer turn: within a few
tenths of a second it is part of that turn, the way a word cut off by a pause is, and farther off
the nearer voice is still a better guess than the main one, which it was only by chance.

A line only another pass heard, whose speaker the vote could not link to the base pass's, carries
that pass's own name for them ("S2~p3", listen/vote.relabel). It names one of the base's speakers,
not yet known which, so since 2026-11-08 it is never left a speaker of its own (it was drawn in a
third colour and dubbed in a third voice): the voice check gives it the speaker whose voice is
nearest (listen/whose.py), and where it could not, it takes the base speaker it overlaps most in
time, else the nearer base turn. Only a voice the check found near no base speaker's (a person the
base pass missed) is kept a speaker of its own, under a name no base speaker has
(listen/follow.adopted, 2026-11-08).
"""
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import replace

from tarjim.models import Word

PASS_TAG = re.compile(r"(?:^|(?<=\.))p\d+\.")
UNLINKED = re.compile(r"~p\d+$")
GAP = 1.0  # seconds of silence that end a line even with the same speaker

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


def unlinked(label: str) -> bool:
    """Whether the label is another pass's name for a speaker the vote could not link."""
    return bool(UNLINKED.search(label))


def based(label: str) -> bool:
    """Whether the label names one of the base pass's speakers."""
    return bool(label) and not unlinked(label)


def nearest(words: list[Word], line: Line, fit: Callable[[str], bool] = bool) -> str:
    """The speaker of the nearer word whose speaker fits (has one, by default) on either side of
    a line, or "" when the clip has none."""
    start, end = span(words, line)
    before = next(((start - w.end, w.speaker) for w in reversed(words[:line[0]])
                   if fit(w.speaker)), None)
    after = next(((w.start - end, w.speaker) for w in words[line[1]:] if fit(w.speaker)), None)
    near = [side for side in (before, after) if side]
    return min(near)[1] if near else ""


def inherited(words: list[Word]) -> list[Word]:
    """The words with each line that has no speaker given to the nearer turn."""
    out = list(words)
    for first, last in lines(words):
        name = "" if words[first].speaker else nearest(words, (first, last))
        if name:
            out[first:last] = [replace(w, speaker=name) for w in out[first:last]]
    return out


def overlapped(words: list[Word], line: Line) -> str:
    """The base speaker whose lines share the most time with a line, or "" when none does."""
    start, end = span(words, line)
    shared: dict[str, float] = {}
    for other in lines(words):
        first, last, name = *span(words, other), words[other[0]].speaker
        if based(name) and min(end, last) > max(start, first):
            shared[name] = shared.get(name, 0.0) + min(end, last) - max(start, first)
    return max(shared, key=shared.__getitem__) if shared else ""


def linked_by_time(words: list[Word]) -> list[Word]:
    """The words with each unlinked line given to the base speaker it overlaps most, else the
    nearer base turn, else (no base speaker in the clip) its own name without the pass tag."""
    out = list(words)
    for line in lines(words):
        label = words[line[0]].speaker
        if unlinked(label):
            name = (overlapped(words, line) or nearest(words, line, based)
                    or UNLINKED.sub("", label))
            out[line[0]:line[1]] = [replace(w, speaker=name) for w in out[line[0]:line[1]]]
    return out
