"""Who is speaking, from the listener's labels. A label may carry the voting pass that found a line
("p2.S1", tarjim/listen/vote.py): that names the pass, not another person. Since 2026-11-09 every
piece of a long video has its labels linked to the clip's names (listen/links.py), so a label
names one speaker in the whole clip, and speakers are ranked by how much they talk in the whole
clip: the one who talks most is the main voice. A transcript kept with no hearing beside it may
still have labels tagged by piece ("c0.S1", "c1.S1"); those are ranked within their piece.

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

Since 2026-11-09 two more labels are unlinked the same way: a line heard again by a request of its
own ("S1~x415", listen/check.relistener), which names speakers its own way, and a piece's speaker
that could not be linked to the clip's names ("S1~k2", listen/links.py). Where no voice placed
the latter, it takes the name before its mark, which links.py chose: its request's own name, or
a new one when another label of its request took that. The nearer turn, most often one of the
piece's other speakers, is the worse guess: its request heard it as someone else. The request's
mark is made by asked_again; a cache written by the branch that named it "~r426" (2026-11-09) is
read the same way.
"""
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import replace
from itertools import count

from tarjim.models import Word

PASS_TAG = re.compile(r"(?:^|(?<=\.))p\d+\.")
# ~p a pass, ~k a piece, ~x a request; ~r a request as reg-misc named it (2026-11-09)
UNLINKED = re.compile(r"(?:~[pkxr]\d+)+$")
PIECE = re.compile(r"^[^~]*~k\d+$")  # a piece's speaker linked to none of the clip's names
REQUEST = re.compile(r"~[xr]\d+$")  # a line heard again by a request of its own
HALF = 0.5  # of its time a line heard again must be said over a turn to be part of it
TOUCH = 0.3  # seconds: ...or this near to one
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


def asked_again(label: str, start: float) -> str:
    """A speaker named in the request that heard a stretch again from `start` s: that request's
    own name for them ("S1~x426"), linked to the clip's speakers by voice, else by time
    (heard_again, 2026-11-09). No speaker stays none."""
    return f"{label}~x{round(start * 10)}" if label else label


def span(words: list[Word], line: Line) -> tuple[float, float]:
    return words[line[0]].start, words[line[1] - 1].end


def unlinked(label: str) -> bool:
    """Whether the label is another pass's name for a speaker the vote could not link."""
    return bool(UNLINKED.search(label))


def based(label: str) -> bool:
    """Whether the label names one of the base pass's speakers."""
    return bool(label) and not unlinked(label)


def sides(words: list[Word], line: Line, fit: Callable[[str], bool]) -> list[tuple[float, str]]:
    """(how far, whose) for the nearer word whose speaker fits on either side of a line."""
    start, end = span(words, line)
    before = next(((start - w.end, w.speaker) for w in reversed(words[:line[0]])
                   if fit(w.speaker)), None)
    after = next(((w.start - end, w.speaker) for w in words[line[1]:] if fit(w.speaker)), None)
    return [side for side in (before, after) if side]


def nearest(words: list[Word], line: Line, fit: Callable[[str], bool] = bool) -> str:
    """The speaker of the nearer word whose speaker fits (has one, by default) on either side of
    a line, or "" when the clip has none."""
    near = sides(words, line, fit)
    return min(near)[1] if near else ""


def inherited(words: list[Word]) -> list[Word]:
    """The words with each line that has no speaker given to the nearer turn."""
    out = list(words)
    for first, last in lines(words):
        name = "" if words[first].speaker else nearest(words, (first, last))
        if name:
            out[first:last] = [replace(w, speaker=name) for w in out[first:last]]
    return out


def shares(words: list[Word], line: Line) -> dict[str, float]:
    """The time each base speaker's lines share with a line."""
    start, end = span(words, line)
    shared: dict[str, float] = {}
    for other in lines(words):
        first, last, name = *span(words, other), words[other[0]].speaker
        if based(name) and min(end, last) > max(start, first):
            shared[name] = shared.get(name, 0.0) + min(end, last) - max(start, first)
    return shared


def overlapped(words: list[Word], line: Line) -> str:
    """The base speaker whose lines share the most time with a line, or "" when none does."""
    shared = shares(words, line)
    return max(shared, key=shared.__getitem__) if shared else ""


def heard_again(words: list[Word], line: Line) -> str:
    """A line heard again by a request of its own (2026-11-09): the turn said over HALF its time
    or more, else the turn within TOUCH of it, else the request's own name for its speaker, as
    before: a turn farther off is as likely the other person's."""
    start, end = span(words, line)
    shared = shares(words, line)
    over = [name for name, seconds in shared.items() if seconds >= HALF * (end - start)]
    touching = [side for side in sides(words, line, based) if side[0] <= TOUCH]
    if over:
        return max(over, key=shared.__getitem__)
    return min(touching)[1] if touching else UNLINKED.sub("", words[line[0]].speaker)


def own_name(label: str, taken: set[str]) -> str:
    """The label without its marks, or the first "S<n>" nobody has when that is taken."""
    name = UNLINKED.sub("", label)
    return name if name not in taken else next(f"S{n}" for n in count(1) if f"S{n}" not in taken)


def placed(words: list[Word], line: Line) -> str:
    """Whose an unlinked line is: a piece's speaker linked to no one takes the name links.py gave
    it, a line heard again goes by the turn it is said in, any other the base speaker it overlaps
    most, else the nearer base turn, else (no base speaker in the clip) its own name without the
    pass tag."""
    label = words[line[0]].speaker
    if PIECE.match(label):
        return UNLINKED.sub("", label)
    if REQUEST.search(label):
        return heard_again(words, line)
    return overlapped(words, line) or nearest(words, line, based) or UNLINKED.sub("", label)


def linked_by_time(words: list[Word]) -> list[Word]:
    """The words with each unlinked line given a base speaker by time (placed)."""
    out = list(words)
    for line in lines(words):
        if unlinked(words[line[0]].speaker):
            name = placed(words, line)
            out[line[0]:line[1]] = [replace(w, speaker=name) for w in out[line[0]:line[1]]]
    return out
