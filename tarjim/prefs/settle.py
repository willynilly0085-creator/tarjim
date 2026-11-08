"""What gives way when settings break a rule between them (2026-11-09).

On save the change that breaks a rule is refused, with an Arabic reason and the nearest value
that would work, and nothing of it is kept. On read (a hand-edited file, or a rule that a new
release made stricter) the offending setting goes back to its default with a note in
server.log, so a job never fails because of a setting. When a preset is applied its own values
stay and the other setting moves to the nearest value that works.
"""
from collections.abc import Iterable
from typing import Any

from tarjim.prefs.checks import RULES, Rule, broken
from tarjim.prefs.spec import Refusal, Spec, Value, refuse
from tarjim.prefs.table import SPECS

SPREAD = 100  # values tried across a range that has no step


def candidates(spec: Spec, near: Any) -> list[Value]:
    if spec.kind == "number":
        step = spec.step or (spec.high - spec.low) / SPREAD
        count = round((spec.high - spec.low) / step)
        grid = [spec.low + i * step for i in range(count + 1)]
        typed = [round(v) if isinstance(spec.default, int) else round(v, 4) for v in grid]
        return sorted(typed, key=lambda v: abs(float(v) - float(near)))
    if spec.kind == "switch":
        return [spec.default, not spec.default]
    if spec.kind == "choice":
        return list(spec.choices)
    if spec.kind == "colour":
        return [spec.default, "#FFFFFF", "#000000"]
    return [spec.default]


def nearest(key: str, values: dict[str, Any], target: str) -> Value | None:
    """The value closest to the one asked for that keeps every rule this setting is in."""
    spec = SPECS[key].at(target)
    rules = rules_with(key)
    for value in candidates(spec, values[key] if spec.kind == "number" else 0):
        trial = {**values, key: value}
        if all(rule.holds(trial, target) for rule in rules):
            return value
    return None


def rules_with(key: str) -> list[Rule]:
    return [rule for rule in RULES if key in rule.keys]


def changes(before: dict[str, Any], wanted: dict[str, Value],
            target: str) -> tuple[dict[str, Any], dict[str, Refusal]]:
    """The values once the wanted changes are made, less each one that breaks a rule. When two
    changes break one rule together, the one asked for last is refused."""
    after, refused = {**before, **wanted}, {}
    for _ in range(len(wanted)):
        left = [k for k in reversed(wanted) if k not in refused]
        found = [rule for rule in broken(after, target) if set(left) & set(rule.keys)]
        if not found:
            break
        culprit = next(k for k in left if k in found[0].keys)
        works = nearest(culprit, after, target)
        refused[culprit] = refuse(SPECS[culprit], found[0].why, works)
        after[culprit] = before[culprit]
    return after, refused


def fallen_back(values: dict[str, Any], target: str,
                defaults: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The values with every setting that breaks a rule back at its default."""
    fixed, notes = dict(values), []
    for _ in range(len(SPECS)):
        found = broken(fixed, target)
        key = next((k for k in reversed(found[0].keys) if fixed[k] != defaults[k]),
                   None) if found else None
        if key is None:
            break
        notes.append(f"preferences: {key} = {fixed[key]!r} breaks a rule with "
                     f"{', '.join(k for k in found[0].keys if k != key)}; back to "
                     f"{defaults[key]!r}")
        fixed[key] = defaults[key]
    return fixed, notes


def made_room(values: dict[str, Any], kept: Iterable[str], target: str) -> dict[str, Any]:
    """The values with the settings outside `kept` moved until every rule holds."""
    fixed, fixed_keys = dict(values), set(kept)
    for _ in range(len(SPECS)):
        found = broken(fixed, target)
        key = next((k for k in reversed(found[0].keys) if k not in fixed_keys),
                   None) if found else None
        works = nearest(key, fixed, target) if key else None
        if key is None or works is None:
            break
        fixed[key] = works
    return fixed


def for_target(values: dict[str, Any], target: str) -> tuple[dict[str, Any], list[str]]:
    """A choice that only one language has: Arabic's own digits are not Persian's or Urdu's."""
    if values["translate.numbers"] == "eastern" and target != "ar":
        return {**values, "translate.numbers": "latin"}, [
            f"preferences: eastern digits are for Arabic only; {target} keeps 0-9"]
    return values, []
