import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from statistics import median

from tarjim.listen.gemini_listen import Utterance

NEAR = 2.0
AGREE = 2
SIMILAR = 0.6
SHARE = 3

Run = list[Utterance]


def norm(word: str) -> str:
    return "".join(re.findall(r"[\w']+", word.lower()))


@dataclass
class Ballot:
    utterance: Utterance
    votes: list[int]
    starts: list[float] = field(default_factory=list)
    ends: list[float] = field(default_factory=list)


def flatten(run: Run) -> list[tuple[int, str]]:
    return [(k, norm(w)) for k, u in enumerate(run) for w in u.text.split()]


def near(a: Utterance, b: Utterance) -> bool:
    return a.start < b.end + NEAR and b.start < a.end + NEAR


def count_votes(base: Run, ballots: list[Ballot], other: Run) -> set[int]:
    left, right = flatten(base), flatten(other)
    matcher = SequenceMatcher(None, [w for _, w in left], [w for _, w in right], autojunk=False)
    used: set[int] = set()
    for block in matcher.get_matching_blocks():
        for step in range(block.size):
            i, j = block.a + step, block.b + step
            mine, theirs = left[i][0], right[j][0]
            if near(base[mine], other[theirs]):
                record(ballots[mine], i - first_index(left, mine), other[theirs])
                used.add(theirs)
    return used


def first_index(flat: list[tuple[int, str]], owner: int) -> int:
    return next(i for i, (k, _) in enumerate(flat) if k == owner)


def record(ballot: Ballot, position: int, backer: Utterance) -> None:
    ballot.votes[position] += 1
    if not comparable(ballot.utterance, backer):
        return
    ballot.starts.append(backer.start)
    ballot.ends.append(backer.end)


def comparable(mine: Utterance, backer: Utterance) -> bool:
    length = mine.end - mine.start
    return abs((backer.end - backer.start) - length) <= max(1.0, length)


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


def extras(leftovers: list[Run], agree: int) -> Run:
    found: Run = []
    for index, run in enumerate(leftovers):
        rest = [u for k, r in enumerate(leftovers) if k != index for u in r]
        for u in run:
            backers = [o for o in rest if similar(u, o)]
            if len(backers) + 1 >= agree and not any(similar(u, f) for f in found):
                found.append(Utterance(u.start, u.end, f"p{index + 2}.{u.speaker}", u.text))
    return found


def vote(runs: list[Run], agree: int = AGREE) -> Run:
    ordered = sorted(runs, key=lambda r: len(flatten(r)), reverse=True)
    base, others = ordered[0], ordered[1:]
    ballots = [Ballot(u, [1] * len(u.text.split())) for u in base]
    leftovers = []
    for other in others:
        used = count_votes(base, ballots, other)
        leftovers.append([u for k, u in enumerate(other) if k not in used])
    kept = [e for b in ballots if (e := elect(b, agree)) is not None]
    return sorted(kept + extras(leftovers, agree), key=lambda u: u.start)
