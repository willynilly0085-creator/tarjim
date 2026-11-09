"""Changing the saved settings, from tarjim's page or from a chat (2026-11-09). Every change
passes the gate and the rules between settings before it is written; one that cannot be taken
is refused with its reason and nothing of it is kept."""
from dataclasses import dataclass, field
from typing import Any

from tarjim import config
from tarjim.languages import LANGUAGES
from tarjim.prefs.model import resolve
from tarjim.prefs.presets import (
    BUILT_IN,
    LONGEST_NAME,
    MOST_OWN,
    OUTSIDE,
    applied,
    languages_in,
    put,
)
from tarjim.prefs.settle import changes
from tarjim.prefs.spec import Refusal, Value, check
from tarjim.prefs.store import for_saving, write
from tarjim.prefs.table import GROUPS, SPECS, in_group


@dataclass
class Outcome:
    saved: list[str] = field(default_factory=list)
    refused: dict[str, str] = field(default_factory=dict)  # key: the Arabic reason


def parsed(wanted: dict[str, Any], language: str) -> tuple[dict[str, Value], dict[str, str]]:
    clean: dict[str, Value] = {}
    refused: dict[str, str] = {}
    for key, raw in wanted.items():
        found = check(SPECS[key].at(language), raw) if key in SPECS else None
        if found is None:
            refused[key] = f"ما فيه إعداد اسمه «{key}»."
        elif isinstance(found, Refusal):
            refused[key] = found.reason
        else:
            clean[key] = found
    return clean, refused


def stored(values: dict[str, Any], key: str, value: Value, language: str) -> None:
    """Keep the value, or forget the key when it is back at its default."""
    spec = SPECS[key]
    kept = put(values.get(key), key, value, language)
    if isinstance(kept, dict):
        kept = {c: v for c, v in kept.items() if v != spec.at(c).default} or None
    elif kept == spec.default:
        kept = None
    if kept is None:
        values.pop(key, None)
    else:
        values[key] = kept


def elsewhere(values: dict[str, Any], clean: dict[str, Value], language: str) -> dict[str, str]:
    """A shared setting must hold in every other language too (2026-11-09): a bigger font
    that French's own longer line no longer fits is refused here, naming French, instead of
    being saved and then quietly undone when a French job reads it."""
    shared = {k: v for k, v in clean.items() if not SPECS[k].per_language}
    refused: dict[str, str] = {}
    for code in sorted((set(LANGUAGES) | languages_in(values)) - {language}):
        left = {k: v for k, v in shared.items() if k not in refused}
        broke = changes(resolve(values, {}, code).values, left, code)[1] if left else {}
        name = LANGUAGES[code].native if code in LANGUAGES else code
        refused |= {k: f"لما تترجم إلى {name}: {r.reason}" for k, r in broke.items()}
    return refused


def change(wanted: dict[str, Any], language: str = "ar") -> Outcome:
    """language: the target language a per-language setting is changed for."""
    with config.SAVING:
        kept = for_saving()
        clean, refused = parsed(wanted, language)
        before = resolve(kept.values, {}, language).values
        after, broke = changes(before, clean, language)
        refused |= {key: refusal.reason for key, refusal in broke.items()}
        # Another language is named only for what this one takes (2026-11-09).
        refused |= elsewhere(kept.values, {k: v for k, v in clean.items() if k not in refused},
                             language)
        saved = [key for key in clean if key not in refused]
        for key in saved:
            stored(kept.values, key, after[key], language)
        if saved:
            write(kept)
    return Outcome(saved, refused)


def reset_keys(what: str) -> list[str]:
    if what == "all":
        return list(SPECS)
    return in_group(what) if what in GROUPS else [what] if what in SPECS else []


def reset_one(values: dict[str, Any], key: str, language: str) -> bool:
    """One setting back to its default; True when something was changed."""
    entry = values.get(key)
    if language and SPECS[key].per_language and isinstance(entry, dict):
        if language not in entry:
            return False
        stored(values, key, SPECS[key].at(language).default, language)
        return True
    return values.pop(key, None) is not None


def reset(what: str = "all", language: str = "") -> list[str]:
    """Back to the default: one setting, a group (a tab of the page) or "all". With a language,
    a per-language setting goes back for that language only, and every shared setting in the
    scope still goes back (2026-11-09): skipping them left them changed with nothing said."""
    with config.SAVING:
        kept = for_saving()
        done = [key for key in reset_keys(what) if reset_one(kept.values, key, language)]
        if done:
            write(kept)
    return done


def use_preset(name: str) -> bool:
    with config.SAVING:
        kept = for_saving()
        chosen = BUILT_IN.get(name, kept.presets.get(name))
        if chosen is None:
            return False
        kept.values = applied(kept.values, chosen)
        write(kept)
    return True


def preset_name(name: str, own: dict[str, Any]) -> str:
    """Why a name cannot be used for the person's own preset, or "" when it can."""
    if not name or len(name) > LONGEST_NAME or not name.isprintable():
        return f"اكتب اسم من حرف إلى {LONGEST_NAME} حرف."
    if name in BUILT_IN:
        return "هالاسم لمجموعة من ترجم نفسه، اختر اسم ثاني."
    if name not in own and len(own) >= MOST_OWN:
        return f"توصل لين {MOST_OWN} مجموعات بس، احذف وحدة قبل."
    return ""


def save_preset(name: str) -> str:
    """The settings changed so far, under a name of the person's own; "" when saved."""
    name = name.strip()
    with config.SAVING:
        kept = for_saving()
        problem = preset_name(name, kept.presets)
        if not problem:
            kept.presets[name] = {k: v for k, v in kept.values.items() if k not in OUTSIDE}
            write(kept)
    return problem


def rename_preset(old: str, new: str) -> str:
    new = new.strip()
    with config.SAVING:
        kept = for_saving()
        own = {k: v for k, v in kept.presets.items() if k != old}
        problem = "ما فيه مجموعة بهالاسم." if old not in kept.presets else preset_name(new, own)
        if not problem:
            kept.presets = {**own, new: kept.presets[old]}
            write(kept)
    return problem


def delete_preset(name: str) -> bool:
    with config.SAVING:
        kept = for_saving()
        found = kept.presets.pop(name, None) is not None
        if found:
            write(kept)
    return found
