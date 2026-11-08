"""What one order keeps of the settings, and the order's own changes checked before its job
starts (2026-11-09). An order keeps only what differs from its language's defaults, with a
version, so an older tarjim, or one whose defaults improved, still reads jobs.json."""
from typing import Any

from tarjim.prefs.model import Prefs, resolve
from tarjim.prefs.settle import changes
from tarjim.prefs.spec import Refusal, check, refuse
from tarjim.prefs.table import SPECS, defaults

VERSION = 1


def vetted(stored: dict[str, Any], tweaks: dict[str, Any],
           target: str) -> dict[str, Refusal]:
    """Why each of one order's own changes cannot be made: an order is refused before its job
    starts, not part way through it."""
    base = resolve(stored, {}, target).values
    refused: dict[str, Refusal] = {}
    clean = {}
    for key, raw in tweaks.items():
        spec = SPECS.get(key)
        if spec is None:
            refused[key] = Refusal(key, f"ما فيه إعداد اسمه «{key}».")
        elif not spec.per_job:
            refused[key] = refuse(spec, "ينحفظ للكل، وما يتغير لفيديو واحد بس")
        elif isinstance(found := check(spec.at(target), raw), Refusal):
            refused[key] = found
        else:
            clean[key] = found
    return {**refused, **changes(base, clean, target)[1]}


def snapshot(prefs: Prefs) -> dict[str, Any]:
    """What one order keeps: only what differs from its language's defaults, so an older
    tarjim, or one whose defaults improved, still reads it (jobs.json)."""
    start = defaults(prefs.target)
    return {"version": VERSION,
            "values": {k: v for k, v in prefs.values.items() if v != start[k]}}


def from_snapshot(kept: Any, target: str) -> Prefs:
    values = kept.get("values") if isinstance(kept, dict) else None
    return resolve(values if isinstance(values, dict) else {}, {}, target)

