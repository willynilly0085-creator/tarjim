"""Who is who across a long clip's pieces, from the sound two neighbouring requests both heard.

Every piece is its own request and a listener numbers its speakers in the order it hears them, so
until 2026-11-09 piece two's "S1" silently named piece one's "S1" even when it was piece one's
"S2", and one person took the other's colour and dub voice from a cut on. Now each request after
the first also hears the end of the piece before it (listen/lead.py), and the words its lead
shares with the earlier piece's lines link its labels to the clip's names, one to one: two labels
of one request are two people, so they never take the same name. Links come from that evidence
first; then the one label left takes the one name left. With no lead to go by (a kept hearing,
music, silence) every label keeps its own name, exactly as before. A label left over in a request
the lead linked otherwise is left unlinked ("S1~k2") for the voice check (listen/whose.py): its
own name is no better than a guess there (measured 2026-11-09: kept, it left the voice check
too mixed to move any line, 0.68 of the speakers right on a seven-piece clip, 1.0 unlinked). A
label the vote could not link inside its piece ("S2~p3") is marked with its piece too, so two
pieces' "S2~p3" are never taken for one speaker.
"""
import itertools
from collections import Counter
from dataclasses import replace
from difflib import SequenceMatcher

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Piece
from tarjim.listen.vote import flatten, linked, near
from tarjim.speakers import based

Run = list[Utterance]
Pairs = Counter[tuple[str, str]]
Names = dict[str, str]


def pairs(base: Run, other: Run) -> Pairs:
    """(base speaker, other speaker) for each word the two say alike near the same time."""
    left, right = flatten(base), flatten(other)
    matcher = SequenceMatcher(None, [w for _, w in left], [w for _, w in right], autojunk=False)
    found: Pairs = Counter()
    for a, b, size in matcher.get_matching_blocks():
        for (k, word), (j, _) in zip(left[a:a + size], right[b:b + size], strict=True):
            if word and near(base[k], other[j]):
                found[base[k].speaker, other[j].speaker] += 1
    return found


def at(run: Run, offset: float) -> Run:
    return [replace(u, start=u.start + offset, end=u.end + offset) for u in run]


def evidence(before: Run, piece: Piece, voted: Run) -> Pairs:
    """(the piece's voted label, the clip's name) and how many words of the lead link them: each
    pass's own labels go to the vote's through the words the pass shares with it, and to the
    clip's through the words its lead shares with the piece before (`before`, at clip times).
    The passes' words are added up before the vote's own rule (vote.linked) is applied: a short
    reply in the lead is two words in each pass, too few in one pass alone."""
    found: Pairs = Counter()
    for run, lead in zip(piece.passes, piece.lead, strict=False):
        mine = linked(pairs(voted, run))
        for (name, label), count in pairs(before, at(lead, piece.start - piece.lead_s)).items():
            if label in mine:
                found[name, mine[label]] += count
    chosen = linked(found)
    return Counter({(label, name): count for (name, label), count in found.items()
                    if chosen.get(label) == name})


def strongest(found: Pairs, labels: list[str]) -> Names:
    """The links the lead heard, the strongest first, never two labels to one name."""
    chosen: Names = {}
    for (label, name), _ in sorted(found.items(), key=lambda item: (-item[1], item[0])):
        if label in labels and label not in chosen and name not in chosen.values():
            chosen[label] = name
    return chosen


def spare(taken: set[str]) -> str:
    return next(f"S{n}" for n in itertools.count(1) if f"S{n}" not in taken)


def assigned(found: Pairs, labels: list[str], names: list[str], k: int) -> Names:
    """Each of piece k's labels as one of the clip's names, one to one (module docstring). A
    label left over in a request the lead linked otherwise is unlinked ("S2~k3"): that request's
    numbering is not the clip's, so the voice check places it; where none runs it is its own name,
    or a new one when another label of its request took that (speakers.linked_by_time)."""
    chosen = strongest(found, labels)
    guards.fired("speaker.linked_piece", len(chosen))
    left = [label for label in labels if label not in chosen]
    free = [name for name in names if name not in chosen.values()]
    if guards.when("speaker.eliminated", bool(chosen) and len(left) == len(free) == 1):
        chosen[left.pop()] = free[0]
    plain = not chosen  # nothing heard to link by: the request's own names stand, as before
    used = {*names, *labels, *chosen.values()}
    for label in left:
        own = label not in chosen.values()
        name = label if own else spare(used)
        alone = guards.when("speaker.unlinked_piece", own and plain)
        guards.when("speaker.apart_piece", not alone)
        chosen[label] = name if alone else f"{name}~k{k}"
        used.add(name)
    return chosen


def labels_of(run: Run) -> list[str]:
    return list(dict.fromkeys(u.speaker for u in run if based(u.speaker)))


def renamed(run: Run, names: Names, k: int) -> Run:
    """The lines under the clip's names; one unlinked in its piece marked with the piece."""
    return [u if not u.speaker else replace(
        u, speaker=names.get(u.speaker) or f"{u.speaker}~k{k}") for u in run]


def named(pieces: list[Piece], voted: list[Run]) -> list[Run]:
    """Each piece's voted lines (at its own times) under the clip's names for its speakers: the
    first piece's as heard, each later one's linked to those before it."""
    out = voted[:1]
    names = labels_of(out[0]) if out else []
    for k in range(1, len(pieces)):
        before = at(out[-1], pieces[k - 1].start)
        found = evidence(before, pieces[k], voted[k])
        chosen = assigned(found, labels_of(voted[k]), names, k)
        out.append(renamed(voted[k], chosen, k))
        names += [name for name in labels_of(out[-1]) if name not in names]
    return out
