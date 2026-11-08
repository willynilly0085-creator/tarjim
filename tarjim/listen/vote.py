"""The lines a majority of listening passes heard, word by word.

Words are split the way the rest of tarjim splits them (scripts.split_words): split on spaces
alone, a Japanese, Chinese or Thai line was one ballot cell that only a letter-perfect copy could
back, so those languages were voted away (2026-11-08)."""
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from statistics import median

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.scripts import split_words

NEAR = 2.0
SIMILAR = 0.6
SHARE = 3
LINKED = 3  # matched words before another pass's speaker is taken for one of the base pass's
LINK_SHARE = 0.6  # ...and the share of its matched words that must sit on that one speaker

Run = list[Utterance]
Pairs = Counter[tuple[str, str]]


def norm(word: str) -> str:
    return "".join(re.findall(r"[\w']+", word.lower()))


def majority(passes: int) -> int:
    """More than half of the passes that heard anything: two of three, three of five. A fixed two
    (until 2026-11-08) let two of five passes outvote the other three."""
    return passes // 2 + 1


@dataclass
class Ballot:
    utterance: Utterance
    votes: list[int]
    starts: list[float] = field(default_factory=list)
    ends: list[float] = field(default_factory=list)
    passes: set[int] = field(default_factory=set)  # the other passes that backed it, by index


def flatten(run: Run) -> list[tuple[int, str]]:
    return [(k, norm(w)) for k, u in enumerate(run) for w in split_words(u.text)]


def ordered(runs: list[Run]) -> list[Run]:
    """Fullest pass first, then the one split into more lines, then by content, so the same
    passes give the same vote whatever order they arrived in (2026-11-08: two passes of equal
    length took the base by arrival order)."""
    return sorted(runs, key=lambda r: (-len(flatten(r)), -len(r),
                                       [(u.start, u.end, u.speaker, u.text) for u in r]))


def near(a: Utterance, b: Utterance) -> bool:
    return a.start < b.end + NEAR and b.start < a.end + NEAR


def count_votes(base: Run, ballots: list[Ballot], other: Run,
                index: int) -> tuple[set[int], Pairs]:
    """The other pass's lines that backed a base word, and which of its speakers sat on which
    of the base's while doing so."""
    left, right = flatten(base), flatten(other)
    firsts = {k: i for i, (k, _) in reversed(list(enumerate(left)))}
    matcher = SequenceMatcher(None, [w for _, w in left], [w for _, w in right], autojunk=False)
    used: set[int] = set()
    pairs: Pairs = Counter()
    for block in matcher.get_matching_blocks():
        for step in range(block.size):
            i, j = block.a + step, block.b + step
            mine, theirs = left[i][0], right[j][0]
            if near(base[mine], other[theirs]):
                record(ballots[mine], i - firsts[mine], other[theirs])
                ballots[mine].passes.add(index)
                used.add(theirs)
                pairs[base[mine].speaker, other[theirs].speaker] += 1
    return used, pairs


def record(ballot: Ballot, position: int, backer: Utterance) -> None:
    ballot.votes[position] += 1
    if not comparable(ballot.utterance, backer):
        return
    ballot.starts.append(backer.start)
    ballot.ends.append(backer.end)


def comparable(mine: Utterance, backer: Utterance) -> bool:
    length = mine.end - mine.start
    return abs((backer.end - backer.start) - length) <= max(1.0, length)


def linked(pairs: Pairs) -> dict[str, str]:
    """Each speaker of another pass as the base pass's speaker it shares words with. Every pass
    numbers its speakers in its own order, so its "S2" may be the base's "S1"."""
    totals: Counter[str] = Counter()
    for (_, theirs), count in pairs.items():
        totals[theirs] += count
    return {theirs: mine for (mine, theirs), count in pairs.items()
            if mine and theirs and count >= LINKED and count >= LINK_SHARE * totals[theirs]}


def relabel(u: Utterance, links: dict[str, str], number: int) -> Utterance:
    """A line only another pass heard, under the base pass's name for its speaker, or a name of
    its own when the passes share too few words to tell. Until 2026-11-08 it was tagged "p3.S2",
    which speakers.who reads as plain "S2": pass 3's S2 silently became the base's S2."""
    if not u.speaker:
        return u
    return Utterance(u.start, u.end, links.get(u.speaker) or f"{u.speaker}~p{number}", u.text)


def elect(ballot: Ballot, agree: int) -> Utterance | None:
    confirmed = sum(v >= agree for v in ballot.votes)
    if confirmed == 0 or confirmed * SHARE < len(ballot.votes):
        return None
    u = ballot.utterance
    start, end = median([u.start, *ballot.starts]), median([u.end, *ballot.ends])
    return Utterance(start, max(start, end), u.speaker, u.text)


def similar(a: Utterance, b: Utterance) -> bool:
    ratio = SequenceMatcher(None, flatten([a]), flatten([b])).ratio()
    return near(a, b) and ratio >= SIMILAR


def backers(u: Utterance, leftovers: list[Run], index: int) -> int:
    """The other passes that heard this line too: one pass hearing it twice is still one pass."""
    return sum(any(similar(u, o) for o in run) for k, run in enumerate(leftovers) if k != index)


Elected = list[tuple[Utterance, set[int]]]


def repeat(u: Utterance, index: int, kept: Elected, found: Run) -> bool:
    """A copy of a line already kept, checked against the kept lines as well (2026-11-08): a
    phrase said twice can pair with its far copy in the base, leaving its near copy over, which
    came back as a second subtitle. A pass that backed the kept line with another of its lines
    heard the phrase twice, so its leftover is the second time it was said (a chant, a refrain)."""
    copy = any(similar(u, f) and index not in heard for f, heard in kept) or any(
        similar(u, f) for f in found)
    return guards.when("vote.extra_dropped", copy)


def extras(leftovers: list[Run], agree: int, kept: Elected) -> Run:
    """Lines the base pass missed and enough other passes heard."""
    found: Run = []
    for index, run in enumerate(leftovers):
        for u in run:
            if backers(u, leftovers, index) + 1 >= agree and not repeat(u, index, kept, found):
                found.append(u)
    return found


def vote(runs: list[Run], agree: int | None = None) -> Run:
    base, *others = ordered(runs)
    needed = majority(sum(1 for run in runs if run)) if agree is None else agree
    ballots = [Ballot(u, [1] * len(split_words(u.text))) for u in base]
    leftovers = []
    for index, other in enumerate(others):
        used, pairs = count_votes(base, ballots, other, index)
        links = linked(pairs)
        leftovers.append([relabel(u, links, index + 2) for k, u in enumerate(other)
                          if k not in used])
    kept = [(e, b.passes) for b in ballots if (e := elect(b, needed)) is not None]
    found = extras(leftovers, needed, kept)
    guards.fired("vote.extras", len(found))
    return sorted([u for u, _ in kept] + found, key=lambda u: u.start)
