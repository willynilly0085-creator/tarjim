"""The settings one job runs with (2026-11-09): every value checked, every rule between them
held, nothing left to parse. resolve() builds them from what was saved and the order's own
changes; a value that cannot be taken is left at its default with a note, never raised."""
from dataclasses import dataclass, field, fields
from typing import Any

from tarjim.prefs.settle import fallen_back, for_target
from tarjim.prefs.spec import Refusal, check
from tarjim.prefs.table import GROUPS, SPECS, defaults


@dataclass(frozen=True)
class Look:
    style: str
    size_wide: int
    size_tall: int
    font: str
    text_colour: str
    box_colour: str
    box_opacity: int
    position: str
    speaker_colours: bool
    mark: bool
    bold: bool
    fade_ms: int
    box_padding: int
    outline_width: int
    outline_colour: str
    shadow: int
    soft_edge: float
    bottom_margin_wide: int
    bottom_margin_tall: int
    top_margin_wide: int
    top_margin_tall: int
    side_margin: int
    speaker_palette: str
    staged_reveal: bool
    mark_size: float
    mark_opacity: int
    mark_side: str
    dialogue_dash: str

    @property
    def palette(self) -> tuple[str, ...]:
        return tuple(self.speaker_palette.split(","))


@dataclass(frozen=True)
class Text:
    reading_cps: float
    line_chars: int
    reading_warning: float
    one_line: bool


@dataclass(frozen=True)
class Timing:
    min_duration: float
    max_duration: float
    linger: float
    min_gap: float
    long_pause: float
    join_gap: float
    min_readable: float
    end_at_cuts: bool
    cut_snap: float
    scene_sensitivity: float
    cut_dialogue_span: float
    dialogue_cues: bool


@dataclass(frozen=True)
class Listen:
    passes: int
    chunk_seconds: int
    gap_seconds: float
    local_backup: bool
    second_opinion: bool
    voice_check: bool
    aligner: str
    reask: str


@dataclass(frozen=True)
class Translate:
    register: str
    numbers: str
    profanity: str
    names: str
    fillers: str
    question_marks: str
    local_backup: bool
    shorten: bool
    length: str


@dataclass(frozen=True)
class Output:
    folder: str
    enlarge: str
    quality: str
    keep_ass: bool
    burn_with_dub: bool


@dataclass(frozen=True)
class Dub:
    balance: int
    gemini_tone: str
    clone_steps: int


@dataclass(frozen=True)
class Prefs:
    target: str
    look: Look
    text: Text
    timing: Timing
    listen: Listen
    translate: Translate
    output: Output
    dub: Dub
    values: dict[str, Any] = field(compare=False, repr=False)  # the same, by key
    notes: tuple[str, ...] = field(default=(), compare=False)


PARTS: dict[str, type[Any]] = dict(zip(GROUPS, (Look, Text, Timing, Listen, Translate, Output,
                                                 Dub), strict=True))


def saved_value(stored: dict[str, Any], key: str, target: str) -> Any:
    """A per-language setting is kept as {language: value}; a job's snapshot holds it bare."""
    raw = stored.get(key)
    if SPECS[key].per_language and isinstance(raw, dict):
        return raw.get(target)
    return raw


def layered(values: dict[str, Any], raws: dict[str, Any], target: str,
            source: str) -> list[str]:
    """Each raw value that passes the gate replaces the one in values; the rest are noted."""
    notes = []
    for key, raw in raws.items():
        found = check(SPECS[key].at(target), raw) if key in SPECS else None
        if isinstance(found, Refusal) or found is None:
            notes.append(f"preferences: {source} {key} = {raw!r} was not taken")
        else:
            values[key] = found
    return notes


def chosen(stored: dict[str, Any], target: str) -> tuple[dict[str, Any], list[str]]:
    """The defaults with each saved value that passes the gate, before the rules between
    settings are held."""
    values = defaults(target)
    saved = {k: saved_value(stored, k, target) for k in stored if k in SPECS}
    notes = layered(values, {k: v for k, v in saved.items() if v is not None}, target, "saved")
    notes += [f"preferences: unknown setting {k!r} left out" for k in stored if k not in SPECS]
    return values, notes


def resolve(stored: dict[str, Any], tweaks: dict[str, Any], target: str) -> Prefs:
    values, notes = chosen(stored, target)
    allowed = {k: v for k, v in tweaks.items() if k in SPECS and SPECS[k].per_job}
    notes += layered(values, allowed, target, "this video's")
    notes += [f"preferences: {k!r} is not changed for one video" for k in tweaks
              if k not in allowed]
    values, fallen = fallen_back(values, target, defaults(target))
    values, adapted = for_target(values, target)
    return built(values, target, (*notes, *fallen, *adapted))


def built(values: dict[str, Any], target: str, notes: tuple[str, ...]) -> Prefs:
    parts = {group: kind(**{f.name: values[f"{group}.{f.name}"] for f in fields(kind)})
             for group, kind in PARTS.items()}
    return Prefs(target, values=values, notes=notes, **parts)
