from dataclasses import dataclass, field

from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.canvas import Canvas, Move
from tarjim.render.paint import alpha_at, ass_colour, tag_colour
from tarjim.render.stages import reveal_at
from tarjim.render.timecode import ass_time
from tarjim.render.voices import BACK_TO_MAIN, Voices, line_voices, voices
from tarjim.rules import DEFAULT_RULES, Rules

RLM = chr(0x200F)
# libass runs the full bidi algorithm only for Encoding -1: with 178 (Arabic), a line holding a
# Latin word ("افتح YouTube ثم") came out in scrambled order.
RIGHT_TO_LEFT = -1
LOOKALIKE_BACKSLASH = "⧵"  # a "\" in the text would start an ASS command such as \N
FADE_MS = 90  # the default of look.fade_ms; a line fades a quarter of its time at most
FADE_SHARE = 4
EVERYTHING = ("\\alpha&HFF&", "\\alpha&H00&")
LETTERS_ONLY = ("\\1a&HFF&\\3a&HFF&", "\\1a&H00&\\3a&H00&")
OUTLINED, BOXED = 1, 4
# The defaults of the person's colours (tarjim/prefs/table_look.py) as tarjim drew them: a warm
# near-black box at about 70% cover, so the picture still shows through and its own text does
# not (the owner, 2026-11-08: whatever sits under the subtitle must never spoil it); outlined
# letters with a 45% black shadow.
SHADOW_COLOUR = "&H8C000000"
OUTLINE_COLOUR = "&H00141414"
BOX_COLOUR = "&H50131415"
BOX_OPACITY, BOX_ALPHA = 69, 0x50
SHADOW_OPACITY, SHADOW_ALPHA = 45, 0x8C
BOTTOM_CENTRE, TOP_CENTRE = 2, 8
SOFT_EDGE = "\\blur0.8"  # a slightly soft outline reads as a studio's, not a hard sticker
TOP_LINE = "{\\an8}"
Spot = tuple[int, bool]
__all__ = ["Canvas", "Move"]  # where the rest of tarjim looks for them

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, \
BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, \
BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{main},{main},{edge},{back},{bold},0,0,0,\
100,100,0,0,{border},{outline},{shadow},{align},{mh},{mh},{mv},{charset}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def colours(canvas: Canvas) -> dict[str, object]:
    """The style's letters, edge and back, from the person's colours (2026-11-09)."""
    look = canvas.look
    box = ass_colour(look.box_colour, alpha_at(look.box_opacity, BOX_OPACITY, BOX_ALPHA))
    shadow = ass_colour("#000000", alpha_at(look.shadow, SHADOW_OPACITY, SHADOW_ALPHA))
    return {"main": ass_colour(look.text_colour), "bold": -1 if look.bold else 0,
            "edge": ass_colour(look.outline_colour),  # dark round the letters, on the box too
            "back": box if canvas.boxed else shadow}


def render_ass(cues: list[Cue], canvas: Canvas, rules: Rules = DEFAULT_RULES) -> str:
    header = HEADER.format(
        w=canvas.width, h=canvas.height, font=canvas.font, size=canvas.font_size,
        outline=canvas.outline, shadow=canvas.shadow, border=BOXED if canvas.boxed else OUTLINED,
        align=TOP_CENTRE if canvas.top else BOTTOM_CENTRE, mh=canvas.margin_h,
        mv=canvas.margin_v, charset=RIGHT_TO_LEFT if rules.rtl else 1, **colours(canvas),
    )
    paint = paint_for(cues, canvas)
    events = [line for cue in cues if cue.text.strip() for line in event_lines(cue, rules, paint)]
    return header + "\n".join(events) + "\n"


@dataclass(frozen=True)
class Paint:
    """What every line of one subtitle file is drawn with."""
    alphas: tuple[str, str] = EVERYTHING
    voices: Voices = field(default_factory=dict)
    edge: str = ""
    spots: dict[tuple[float, float], Spot] = field(default_factory=dict)
    fade_ms: int = FADE_MS
    main: str = BACK_TO_MAIN

    def fade(self, start: float, end: float) -> int:
        """A line cut short by a scene change fades a quarter of its time at most (2026-11-09)."""
        return max(0, min(self.fade_ms, int((end - start) * 1000 / FADE_SHARE)))


def paint_for(cues: list[Cue], canvas: Canvas) -> Paint:
    look = canvas.look
    edge = "" if canvas.boxed else f"\\blur{look.soft_edge:g}"
    return Paint(LETTERS_ONLY if canvas.boxed else EVERYTHING, voices(cues, look), edge,
                 {(s, e): (m, t) for s, e, m, t in canvas.moves}, look.fade_ms,
                 tag_colour(look.text_colour))


def event_lines(cue: Cue, rules: Rules, paint: Paint | None = None) -> list[str]:
    paint = paint or Paint()
    mark = RLM if rules.rtl else ""
    shown = display_lines(cue.text, rules)
    lines = [f"{colour}{mark}{clean(line)}{mark}" for colour, line in zip(
        line_voices(cue, len(shown), paint.voices, paint.main), shown, strict=True)]
    moment, spot = reveal_at(cue, rules), paint.spots.get((cue.start, cue.end))
    if moment is None:
        both = paint.fade(cue.start, cue.end)
        return [event(cue.start, cue.end, fade(both, both, paint.edge) + "\\N".join(lines), spot)]
    hide, show = paint.alphas
    *first, last = lines
    before, after = paint.fade(cue.start, moment), paint.fade(moment, cue.end)
    waiting = "\\N".join([*first, f"{{{hide}}}" + last])
    # libass reads \t(0,0,...) as the whole event: with no fade the line shows at once (2026-11-09)
    reveal = f"{{{hide}\\t(0,{after},{show})}}" if after else f"{{{show}}}"
    arriving = "\\N".join([*first, reveal + last])
    return [event(cue.start, moment, fade(before, 0, paint.edge) + waiting, spot),
            event(moment, cue.end, fade(0, after, paint.edge) + arriving, spot)]


def event(start: float, end: float, body: str, spot: Spot | None = None) -> str:
    """A line in the style's place (MarginV 0), or in a place of its own."""
    margin, top = spot or (0, False)
    tag = TOP_LINE if top else ""
    return f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,{margin},,{tag}{body}"


def fade(fade_in: int, fade_out: int, edge: str = "") -> str:
    return f"{{\\fad({fade_in},{fade_out}){edge}}}"


def clean(text: str) -> str:
    return (text.replace("\\", LOOKALIKE_BACKSLASH).replace("{", "(").replace("}", ")")
            .replace("\n", " "))
