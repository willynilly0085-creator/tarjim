"""Ready sets of settings (2026-11-09). A preset changes only the settings it names: each is
first put back to its default and then set, so the result never depends on what came before,
and the person's own font, colours and mark stay as they are. A setting kept per language is
given as a share of each language's own default, so Japanese is never asked to read at an
Arabic speed. Every preset passes the same gate and rules as any other change."""
from dataclasses import dataclass
from typing import Any

from tarjim.languages import LANGUAGES
from tarjim.prefs.model import chosen
from tarjim.prefs.settle import made_room
from tarjim.prefs.spec import Value, typed
from tarjim.prefs.table import SPECS

# Never part of a preset: what the person chose for their own videos and their own computer.
OUTSIDE = frozenset({"look.mark", "look.font", "output.folder"})
ORIGINAL = "original"  # everything as tarjim does it out of the box, but OUTSIDE
MOST_OWN = 10
LONGEST_NAME = 40


@dataclass(frozen=True)
class Share:
    """A per-language setting at this percentage of each language's default."""
    percent: float


BUILT_IN: dict[str, dict[str, Value | Share]] = {
    ORIGINAL: {},
    "calm": {"look.size_wide": 95, "look.size_tall": 95, "look.fade_ms": 100,
             "look.bold": False, "timing.linger": 0.6, "timing.min_duration": 0.9},
    # The line still rises over name captions and tickers: that is what news shows have most.
    "news": {"look.box_opacity": 90, "look.staged_reveal": False,
             "translate.register": "formal", "translate.names": "target"},
    "bold": {"look.size_wide": 115, "look.size_tall": 115, "look.style": "outline",
             "look.outline_width": 12, "look.shadow": 70},
    "phone": {"look.size_wide": 110, "look.size_tall": 110, "look.bottom_margin_tall": 16,
              "text.line_chars": Share(80)},
    "easy": {"text.reading_cps": Share(90), "timing.min_duration": 1.0,
             "timing.min_readable": 1.0, "timing.max_duration": 7.0, "timing.linger": 0.6},
    "verbatim": {"translate.fillers": "keep", "translate.question_marks": "keep",
                 "text.reading_cps": Share(120)},
}


def share_of(key: str, share: Share, code: str) -> Value:
    spec = SPECS[key].at(code)
    wanted = float(spec.default) * share.percent / 100
    on_step = spec.low + round((wanted - spec.low) / spec.step) * spec.step
    return typed(spec, min(max(on_step, spec.low), spec.high))


def stored_form(key: str, value: Any) -> Any:
    """A value as the file keeps it: nothing that equals its default."""
    spec = SPECS[key]
    if isinstance(value, Share):
        value = {code: share_of(key, value, code) for code in LANGUAGES}
    if isinstance(value, dict):
        kept = {code: v for code, v in value.items() if v != spec.at(code).default}
        return kept or None
    return None if value == spec.default else value


def applied(stored: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
    if preset is BUILT_IN[ORIGINAL]:
        return {k: v for k, v in stored.items() if k in OUTSIDE}
    named = {k: v for k, v in preset.items() if k in SPECS and k not in OUTSIDE}
    out = {k: v for k, v in stored.items() if k not in named}
    for key, value in named.items():
        kept = stored_form(key, value)
        if kept is not None:
            out[key] = kept
    return made_way(out, set(named))


def languages_in(stored: dict[str, Any]) -> set[str]:
    return {"ar"} | {code for v in stored.values() if isinstance(v, dict) for code in v}


def made_way(stored: dict[str, Any], kept: set[str]) -> dict[str, Any]:
    """Settings the preset does not name move just enough for its own to hold (a bigger font
    shortens a line length that would no longer fit)."""
    out = dict(stored)
    for code in sorted(languages_in(stored)):
        values = chosen(out, code)[0]
        for key, value in made_room(values, kept, code).items():
            if value != values[key]:
                out[key] = put(out.get(key), key, value, code)
    return out


def put(old: Any, key: str, value: Value, code: str) -> Any:
    spec = SPECS[key]
    if not spec.per_language:
        return value
    return {**(old if isinstance(old, dict) else {}), code: value}


def active(stored: dict[str, Any], own: dict[str, dict[str, Any]]) -> str:
    """The preset the saved settings are exactly, or "" when they are the person's own mix."""
    every = {**own, **BUILT_IN}  # a name of tarjim's own is never the person's
    base = applied(stored, BUILT_IN[ORIGINAL])
    return next((name for name in (*BUILT_IN, *own)
                 if applied(base, every[name]) == stored), "")
