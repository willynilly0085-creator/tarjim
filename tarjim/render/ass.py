from dataclasses import dataclass, field

from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.stages import reveal_at
from tarjim.render.timecode import ass_time
from tarjim.render.voices import MAIN, Voices, line_voices, voices
from tarjim.rules import DEFAULT_RULES, Rules

RLM = chr(0x200F)
ARABIC_CHARSET = 178
FADE_MS = 90
EVERYTHING = ("\\alpha&HFF&", "\\alpha&H00&")
LETTERS_ONLY = ("\\1a&HFF&\\3a&HFF&", "\\1a&H00&\\3a&H00&")
PORTRAIT_FONT = 0.066
LANDSCAPE_FONT = 0.058
OUTLINED, BOXED = 1, 4
SHADOW_COLOUR = "&H8C000000"
OUTLINE_COLOUR = "&H00141414"
BOX_COLOUR = "&H3A141414"
BOX_PADDING = 0.22
BOTTOM_CENTRE, TOP_CENTRE = 2, 8
SOFT_EDGE = "\\blur0.8"  # a slightly soft outline reads as a studio's, not a hard sticker

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
Style: Default,{font},{size},{main},{main},{edge},{back},-1,0,0,0,\
100,100,0,0,{border},{outline},{shadow},{align},{mh},{mh},{mv},{charset}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    font: str = "Dubai"
    bright: bool = False
    # Where the picture's own text leaves room (render/placement.py): a distance from the bottom
    # edge, or from the top edge when top is set. None is the usual place.
    margin: int | None = None
    top: bool = False
    # The picture's own text bands (render/text_bands.py), for tarjim's mark (render/mark.py).
    # They say what the picture holds, not where the subtitle goes, so equality leaves them out.
    bands: tuple[tuple[float, float], ...] = field(default=(), compare=False)

    @property
    def portrait(self) -> bool:
        return self.height > self.width

    @property
    def font_size(self) -> int:
        ratio = PORTRAIT_FONT if self.portrait else LANDSCAPE_FONT
        return round(min(self.width, self.height) * ratio)

    @property
    def margin_v(self) -> int:
        if self.margin is not None:
            return self.margin
        return round(self.height * (0.14 if self.portrait else 0.07))

    @property
    def margin_h(self) -> int:
        return round(self.width * 0.06)

    @property
    def outline(self) -> int:
        return 1 if self.bright else max(2, round(self.font_size * 0.08))

    @property
    def shadow(self) -> int:
        if self.bright:
            return max(4, round(self.font_size * BOX_PADDING))
        return max(1, self.outline // 2)


def render_ass(cues: list[Cue], canvas: Canvas, rules: Rules = DEFAULT_RULES) -> str:
    header = HEADER.format(
        w=canvas.width, h=canvas.height, font=canvas.font, size=canvas.font_size,
        outline=canvas.outline, shadow=canvas.shadow, border=BOXED if canvas.bright else OUTLINED,
        edge=BOX_COLOUR if canvas.bright else OUTLINE_COLOUR,
        back=BOX_COLOUR if canvas.bright else SHADOW_COLOUR,
        align=TOP_CENTRE if canvas.top else BOTTOM_CENTRE, mh=canvas.margin_h,
        mv=canvas.margin_v, charset=ARABIC_CHARSET if rules.rtl else 1, main=MAIN,
    )
    look = Look(LETTERS_ONLY if canvas.bright else EVERYTHING, voices(cues),
                "" if canvas.bright else SOFT_EDGE)
    events = [line for cue in cues if cue.text.strip() for line in event_lines(cue, rules, look)]
    return header + "\n".join(events) + "\n"


@dataclass(frozen=True)
class Look:
    alphas: tuple[str, str] = EVERYTHING
    voices: Voices = field(default_factory=dict)
    edge: str = ""


def event_lines(cue: Cue, rules: Rules, look: Look | None = None) -> list[str]:
    look = look or Look()
    mark = RLM if rules.rtl else ""
    shown = display_lines(cue.text, rules)
    lines = [f"{colour}{mark}{clean(line)}{mark}"
             for colour, line in zip(line_voices(cue, len(shown), look.voices), shown, strict=True)]
    moment = reveal_at(cue)
    if moment is None:
        return [event(cue.start, cue.end, fade(FADE_MS, FADE_MS, look.edge) + "\\N".join(lines))]
    hide, show = look.alphas
    *first, last = lines
    waiting = "\\N".join([*first, f"{{{hide}}}" + last])
    arriving = "\\N".join([*first, f"{{{hide}\\t(0,{FADE_MS},{show})}}" + last])
    return [event(cue.start, moment, fade(FADE_MS, 0, look.edge) + waiting),
            event(moment, cue.end, fade(0, FADE_MS, look.edge) + arriving)]


def event(start: float, end: float, body: str) -> str:
    return f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{body}"


def fade(fade_in: int, fade_out: int, edge: str = "") -> str:
    return f"{{\\fad({fade_in},{fade_out}){edge}}}"


def clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ")
