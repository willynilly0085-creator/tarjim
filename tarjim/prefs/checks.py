"""The rules that tie settings together (2026-11-09). Each reads the values for one target
language and says whether they hold; prefs/settle.py decides what gives way when one breaks."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from tarjim.languages import language
from tarjim.prefs.colour import over_white, rgb, stands_out
from tarjim.prefs.table_look import LANDSCAPE_FONT, PORTRAIT_FONT
from tarjim.rules import letter_width

Values = Mapping[str, Any]
NEAR = 1e-6
# The picture a saved line length is held to: a wide 1080p frame. A standing video, or one
# narrower than 16:9, is given a shorter line when its job starts (line_chars_for).
WIDE_FRAME = (1920, 1080)


@dataclass(frozen=True)
class Rule:
    keys: tuple[str, ...]  # what it reads; when a saved file breaks it, the last gives way first
    holds: Callable[[Values, str], bool]
    why: str  # Arabic, naming the settings it ties together


def letters_stand_out(values: Values, _target: str) -> bool:
    """The words and every speaker's colour stand out from the box over a white picture, or
    from the letters' own edge when there is no box."""
    if values["look.style"] == "box":
        behind = over_white(values["look.box_colour"], values["look.box_opacity"])
    else:
        behind = rgb(values["look.outline_colour"])
    shown = [values["look.text_colour"]]
    if values["look.speaker_colours"]:
        shown += str(values["look.speaker_palette"]).split(",")
    return all(stands_out(c, behind) for c in shown)


def widest_line(values: Values, target: str, frame: tuple[int, int]) -> int:
    """How many letters one line holds on this picture, as render/room.py measures it: the
    drawn font size and a letter width kept on the wide side (rules.letter_width)."""
    width, height = frame
    portrait = height > width
    size = values["look.size_tall" if portrait else "look.size_wide"] / 100
    font = round(min(width, height) * (PORTRAIT_FONT if portrait else LANDSCAPE_FONT) * size)
    free = width - 2 * round(width * values["look.side_margin"] / 100) - 2 * edge(values, font)
    return int(free / (max(font, 1) * letter_width(language(target))))


def edge(values: Values, font: int) -> int:
    """What the box (its padding) or the outlined letters (their shadow) add on each side."""
    if values["look.style"] == "box":
        return max(4, round(font * float(values["look.box_padding"]) / 100))
    return max(1, max(2, round(font * float(values["look.outline_width"]) / 100)) // 2)


def line_fits(values: Values, target: str) -> bool:
    return bool(values["text.line_chars"] <= widest_line(values, target, WIDE_FRAME))


def line_chars_for(values: Values, target: str, frame: tuple[int, int]) -> int:
    """The line length one picture can take: the setting, or less on a standing video."""
    return int(min(values["text.line_chars"], widest_line(values, target, frame)))


RULES: tuple[Rule, ...] = (
    Rule(("timing.min_duration", "timing.min_readable"),
         lambda v, _t: v["timing.min_readable"] >= v["timing.min_duration"] - NEAR,
         "الكلام القصير لازم يندمج لين يوصل «أقل مدة يبقى فيها السطر» على الأقل"),
    Rule(("timing.long_pause", "timing.join_gap"),
         lambda v, _t: v["timing.join_gap"] < v["timing.long_pause"] - NEAR,
         "السكتة اللي يندمج عبرها الكلام لازم تكون أقصر من «سكتة بهالطول تبدأ سطر جديد»"),
    Rule(("timing.min_duration", "timing.min_gap"),
         lambda v, _t: v["timing.min_gap"] <= v["timing.min_duration"] / 4 + NEAR,
         "الفراغ بين السطور لازم ما يزيد عن ربع «أقل مدة يبقى فيها السطر»"),
    Rule(("look.style", "look.speaker_colours", "look.box_colour", "look.outline_colour",
          "look.speaker_palette", "look.box_opacity", "look.text_colour"), letters_stand_out,
         "الكلام وألوان المتكلمين لازم تبين على الخلفية حتى فوق صورة بيضاء (تباين 4.5 على الأقل)"),
    Rule(("look.style", "look.box_padding", "look.outline_width", "look.side_margin",
          "look.size_wide", "text.line_chars"), line_fits,
         "السطر لازم يدخل في عرض الفيديو العرضي بهالحجم وهالمسافة من الجوانب"),
    Rule(("timing.dialogue_cues", "text.one_line"),
         lambda v, _t: not (v["text.one_line"] and v["timing.dialogue_cues"]),
         "السطر الواحد ما يشيل متكلمين اثنين؛ طف «متكلمين اثنين بنفس السطر بشرطة» قبل"),
)


def broken(values: Values, target: str) -> list[Rule]:
    return [rule for rule in RULES if not rule.holds(values, target)]
