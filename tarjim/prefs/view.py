"""The settings as tarjim's page and a chat see them, and the checks a save adds to the gate
(2026-11-09): the table of every setting for one language, the values in force, what differs
from the original, which settings do nothing with the others as they are, and a trial of
values not saved yet, for the preview."""
from collections.abc import Callable, Mapping
from typing import Any

from tarjim.config import setting
from tarjim.languages import LANGUAGES, language
from tarjim.prefs.edit import change, parsed
from tarjim.prefs.model import Prefs, resolve
from tarjim.prefs.presets import BUILT_IN, active
from tarjim.prefs.settle import changes
from tarjim.prefs.spec import Spec
from tarjim.prefs.store import current, load
from tarjim.prefs.table import GROUPS, SPECS, defaults, in_group

Values = Mapping[str, Any]
BOX_ONLY = ("look.box_colour", "look.box_opacity", "look.box_padding")
OUTLINE_ONLY = ("look.outline_width", "look.outline_colour", "look.shadow", "look.soft_edge")
MARK = ("look.mark_size", "look.mark_opacity", "look.mark_side")
DIALOGUE = ("look.staged_reveal", "look.dialogue_dash")
HEARD_ONCE = ("openai", "local")  # one pass only: the passes setting does nothing for them
# Settings that do nothing with the others as they are: greyed on the page, with the reason.
IDLE: tuple[tuple[tuple[str, ...], Callable[[Values, str], bool], str], ...] = (
    (BOX_ONLY, lambda v, _t: v["look.style"] != "box", "يشتغل مع شكل «على خلفية» بس"),
    (OUTLINE_ONLY, lambda v, _t: v["look.style"] != "outline",
     "يشتغل مع شكل «حروف بحدود» بس"),
    (("look.speaker_palette",), lambda v, _t: not v["look.speaker_colours"],
     "يشتغل لما يكون «لون لكل متكلم» شغّال"),
    (MARK, lambda v, _t: not v["look.mark"], "يشتغل لما يكون «شعار ترجم على الفيديو» شغّال"),
    (DIALOGUE, lambda v, _t: not v["timing.dialogue_cues"],
     "يشتغل لما يكون «متكلمين اثنين بنفس السطر» شغّال"),
    (("listen.passes",), lambda _v, _t: setting("listen_provider") in HEARD_ONCE,
     "السماع اللي اخترته يسمع مرة وحدة بس"),
    (("listen.second_opinion",), lambda _v, _t: setting("listen_provider") == "local",
     "السماع أصلاً على جهازك"),
    (("translate.numbers",), lambda v, t: t != "ar" and v["translate.numbers"] == "eastern",
     "الأرقام الشرقية للعربي بس، وهاللغة تنكتب أرقامها 0-9"),
)


def row(spec: Spec) -> dict[str, Any]:
    # "whole" (2026-11-09): 17.0 reaches the page's script as 17, so the default cannot tell
    # it a decimal setting; it rounded 17.5 letters a second to 18 and a 0.4 s gap to 0.
    whole = isinstance(spec.default, int) and not isinstance(spec.default, bool)
    return {"key": spec.key, "group": spec.group, "tier": spec.tier, "kind": spec.kind,
            "label": spec.label, "default": spec.default, "low": spec.low, "high": spec.high,
            "step": spec.step, "whole": whole, "choices": list(spec.choices),
            "per_language": spec.per_language, "per_job": spec.per_job}


def everywhere(values: Values, target: str) -> tuple[list[str], bool]:
    """What reset("all") puts back, in every language, and whether that reaches another
    language's own values (2026-11-09): the page counted only the language it shows."""
    keys = [k for k in SPECS if values.get(k) is not None]
    others = any(isinstance(values[k], dict) and set(values[k]) - {target} for k in keys)
    return keys, others


def idle(values: Values, target: str) -> dict[str, str]:
    return {key: f"«{SPECS[key].label}»: {why}." for keys, test, why in IDLE
            if test(values, target) for key in keys}


def state(target: str, group: str = "") -> dict[str, Any]:
    """Everything the settings page or a chat needs for one language, or one group of it."""
    kept, prefs, start = load(), current(target), defaults(target)
    keys = in_group(group) if group else list(SPECS)
    quiet = idle(prefs.values, target)
    everything, others = everywhere(kept.values, target)
    return {"language": target, "groups": list(GROUPS),
            "specs": [row(SPECS[k].at(target)) for k in keys],
            "values": {k: prefs.values[k] for k in keys},
            "changed": [k for k in keys if prefs.values[k] != start[k]],
            "changed_all": everything, "others": others,
            "idle": {k: why for k, why in quiet.items() if k in keys},
            "preset": active(kept.values, kept.presets),
            "presets": {"built_in": list(BUILT_IN), "own": sorted(kept.presets)},
            "notes": list(prefs.notes)}


def font_refused(wanted: Values, target: str) -> dict[str, str]:
    """A font must be on this computer and write the language's letters (2026-11-09): libass
    draws a missing one's letters as boxes. The language's own font is always taken."""
    name = wanted.get("look.font")
    if not isinstance(name, str) or name.strip().lower() == language(target).font.lower():
        return {}
    from tarjim.render.font_cover import writes

    others = writes(name, target)
    if others is None:
        return {}
    native = language(target).native
    return {"look.font": f"«{SPECS['look.font'].label}»: «{name.strip()}» مو موجود على جهازك "
                         f"أو ما يكتب حروف {native}. اختر من: {'، '.join(others[:6])}."}


def save(wanted: Values, target: str) -> dict[str, Any]:
    """POST /prefs and change_preferences: what was saved, what was refused and why."""
    fonts = font_refused(wanted, target)
    outcome = change({k: v for k, v in wanted.items() if k not in fonts}, target)
    refused = {**outcome.refused, **fonts}
    return {"saved": outcome.saved, "refused": refused, "notes": notes(outcome.saved, target)}


def notes(saved: list[str], target: str) -> list[str]:
    quiet = idle(current(target).values, target)
    name = LANGUAGES[target].native if target in LANGUAGES else target
    only = [f"«{SPECS[k].label}» انحفظ للغة {name} بس." for k in saved if SPECS[k].per_language]
    return only + [quiet[k] for k in saved if k in quiet]


def trial(wanted: Values, target: str) -> tuple[Prefs, dict[str, str]]:
    """The settings with values not saved yet, each through the gate and the rules, for the
    preview; what cannot be taken is left as saved and said why."""
    clean, refused = parsed(dict(wanted), target)
    refused |= font_refused(wanted, target)
    clean = {k: v for k, v in clean.items() if k not in refused}
    before = resolve(load().values, {}, target).values
    after, broke = changes(before, clean, target)
    refused |= {key: refusal.reason for key, refusal in broke.items()}
    return resolve(after, {}, target), refused
