"""The lead each piece's request heard too (tarjim/listen/lead.py, 2026-11-09), for faults.py.

A request after the first also hears the last seconds of the piece before it. Its lead lines are
that piece's lines in the same pass, with the faults already in them, named the way this request
names its speakers: a person is named as in their first line of the request, and one it does not
otherwise hear takes the first "S<n>" it has not used. So `labels_permuted` can be linked only
through the lead, as live. A tarjim without leads (a baseline before 2026-11-09) gets none.
"""
from dataclasses import fields
from itertools import count
from typing import Any

from tarjim.listen.coverage import merged
from tarjim.listen.merge import Piece

Line = dict[str, Any]
Span = tuple[float, float]


def supported() -> bool:
    return any(f.name == "lead" for f in fields(Piece))


def seconds(truth: dict[str, Any], pieces: list[Span], size: float) -> list[float]:
    """Each piece's lead, as tarjim chooses it from the voice detector's speech."""
    from tarjim.listen.lead import lead_of

    speech = merged([(w["start"], w["end"]) for w in truth["words"]
                     if not w.get("background")], 0.0)
    return [lead_of(pieces, k, speech, size) for k in range(len(pieces))]


def person(truth: dict[str, Any], line: Line) -> str | None:
    ids = line.get("ids") or []
    return str(truth["sentences"][ids[0]]["speaker"]) if ids else None


def names_in(truth: dict[str, Any], run: list[Line]) -> dict[str, str]:
    """Each truth speaker as the request names them: the label of their first line in it."""
    order: dict[str, str] = {}
    for line in sorted(run, key=lambda x: x["start"]):
        if (who := person(truth, line)) is not None:
            order.setdefault(who, str(line["speaker"]))
    return order


def heard(truth: dict[str, Any], before: list[Line], run: list[Line], lead: Span) -> list[Line]:
    """The lines of the pass before whose middle is inside the lead, named as in `run`."""
    names = names_in(truth, run)
    used = set(names.values())
    out = []
    for line in sorted(before, key=lambda x: x["start"]):
        who = person(truth, line)
        if who is None or not lead[0] <= (line["start"] + line["end"]) / 2 < lead[1]:
            continue
        if who not in names:
            names[who] = next(f"S{n}" for n in count(1) if f"S{n}" not in used)
            used.add(names[who])
        out.append({**line, "speaker": names[who]})
    return out


def leads(truth: dict[str, Any], pieces: list[Span], passes: list[list[list[Line]]],
          size: float) -> list[tuple[float, list[list[Line]]]]:
    """Each piece's lead seconds and each pass's lead lines (none for the first piece)."""
    out: list[tuple[float, list[list[Line]]]] = []
    for k, lead_s in enumerate(seconds(truth, pieces, size)):
        span = (pieces[k][0] - lead_s, pieces[k][0])
        out.append((lead_s, [heard(truth, passes[k - 1][n], run, span)
                             for n, run in enumerate(passes[k])] if lead_s > 0 else []))
    return out
