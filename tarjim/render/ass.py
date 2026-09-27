from dataclasses import dataclass

from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.stages import reveal_at
from tarjim.render.timecode import ass_time
from tarjim.rules import DEFAULT_RULES, Rules

RLM = chr(0x200F)
ARABIC_CHARSET = 178
FADE_MS = 90
HIDDEN = "{\\alpha&HFF&}"
APPEAR = f"{{\\alpha&HFF&\\t(0,{FADE_MS},\\alpha&H00&)}}"
PORTRAIT_FONT = 0.066
LANDSCAPE_FONT = 0.058
OUTLINED, BOXED = 1, 3
OUTLINE_COLOUR = "&H00141414"
BOX_COLOUR = "&H3A141414"
BOX_PADDING = 0.3

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, \
BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, \
BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,{edge},&H8C000000,-1,0,0,0,\
100,100,0,0,{border},{outline},{shadow},2,{mh},{mh},{mv},{charset}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    font: str = "Dubai"
    bright: bool = False

    @property
    def portrait(self) -> bool:
        return self.height > self.width

    @property
    def font_size(self) -> int:
        ratio = PORTRAIT_FONT if self.portrait else LANDSCAPE_FONT
        return round(min(self.width, self.height) * ratio)

    @property
    def margin_v(self) -> int:
        return round(self.height * (0.14 if self.portrait else 0.07))

    @property
    def margin_h(self) -> int:
        return round(self.width * 0.06)

    @property
    def outline(self) -> int:
        if self.bright:
            return max(4, round(self.font_size * BOX_PADDING))
        return max(2, round(self.font_size * 0.08))

    @property
    def shadow(self) -> int:
        return 0 if self.bright else max(1, self.outline // 2)


def render_ass(cues: list[Cue], canvas: Canvas, rules: Rules = DEFAULT_RULES) -> str:
    header = HEADER.format(
        w=canvas.width, h=canvas.height, font=canvas.font, size=canvas.font_size,
        outline=canvas.outline, shadow=canvas.shadow, border=BOXED if canvas.bright else OUTLINED,
        edge=BOX_COLOUR if canvas.bright else OUTLINE_COLOUR,
        mh=canvas.margin_h, mv=canvas.margin_v, charset=ARABIC_CHARSET if rules.rtl else 1,
    )
    events = [line for cue in cues if cue.text.strip() for line in event_lines(cue, rules)]
    return header + "\n".join(events) + "\n"


def event_lines(cue: Cue, rules: Rules) -> list[str]:
    mark = RLM if rules.rtl else ""
    lines = [f"{mark}{clean(line)}{mark}" for line in display_lines(cue.text, rules)]
    moment = reveal_at(cue)
    if moment is None:
        return [event(cue.start, cue.end, fade(FADE_MS, FADE_MS) + "\\N".join(lines))]
    *first, last = lines
    waiting = "\\N".join([*first, HIDDEN + last])
    arriving = "\\N".join([*first, APPEAR + last])
    return [event(cue.start, moment, fade(FADE_MS, 0) + waiting),
            event(moment, cue.end, fade(0, FADE_MS) + arriving)]


def event(start: float, end: float, body: str) -> str:
    return f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{body}"


def fade(fade_in: int, fade_out: int) -> str:
    return f"{{\\fad({fade_in},{fade_out})}}"


def clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ")
