"""The picture a subtitle is drawn on and the sizes drawn on it, from the person's settings.

Moved out of render/ass.py on 2026-11-09, when the sizes, margins, paddings and outline stopped
being fixed parts of the picture: each is now a percentage the person chose (tarjim/prefs), and
the defaults are the parts tarjim drew before, so a person who changed nothing gets the same
subtitles to the byte.
"""
from dataclasses import dataclass, field

from tarjim.prefs.model import Look, resolve
from tarjim.prefs.table_look import LANDSCAPE_FONT, PORTRAIT_FONT

DEFAULT_LOOK = resolve({}, {}, "ar").look
# One line drawn somewhere other than the video's place (render/moments.py): its start and end,
# then its distance from the bottom edge, or from the top edge when the flag is set.
Move = tuple[float, float, int, bool]
GAP = 0.3  # kept above the picture's own text, as a part of the font size (render/placement)
GAP_PAST_PADDING = 0.08  # and never less than the box's padding and this


def part(value: float) -> float:
    """A percentage as a part: 7 is exactly 0.07, as the fixed parts were written."""
    return value / 100


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    font: str = "Dubai"
    # Every line sits on its own see-through box; False draws the older outlined letters.
    boxed: bool = True
    # Where the picture's own text leaves room (render/placement.py): a distance from the bottom
    # edge, or from the top edge when top is set. None is the usual place.
    margin: int | None = None
    top: bool = False
    # The picture's own text bands (render/text_bands.py), for tarjim's mark (render/mark.py).
    # They say what the picture holds, not where the subtitle goes, so equality leaves them out.
    bands: tuple[tuple[float, float], ...] = field(default=(), compare=False)
    moves: tuple[Move, ...] = ()
    look: Look = DEFAULT_LOOK

    @classmethod
    def drawn(cls, size: tuple[int, int], look: Look, font: str) -> "Canvas":
        """The canvas for one picture as the person set it up (2026-11-09)."""
        return cls(size[0], size[1], font, look.style == "box", look=look)

    @property
    def portrait(self) -> bool:
        return self.height > self.width

    @property
    def font_size(self) -> int:
        ratio = PORTRAIT_FONT if self.portrait else LANDSCAPE_FONT
        size = self.look.size_tall if self.portrait else self.look.size_wide
        return round(min(self.width, self.height) * ratio * part(size))

    @property
    def usual_margin(self) -> int:
        """The distance from the bottom edge when nothing moved the subtitle."""
        look = self.look
        below = look.bottom_margin_tall if self.portrait else look.bottom_margin_wide
        return round(self.height * part(below))

    @property
    def top_margin(self) -> int:
        """The distance from the top edge when the subtitle goes there."""
        look = self.look
        above = look.top_margin_tall if self.portrait else look.top_margin_wide
        return round(self.height * part(above))

    @property
    def margin_v(self) -> int:
        return self.usual_margin if self.margin is None else self.margin

    @property
    def margin_h(self) -> int:
        return round(self.width * part(self.look.side_margin))

    @property
    def outline(self) -> int:
        return 1 if self.boxed else max(2, round(self.font_size * part(self.look.outline_width)))

    @property
    def shadow(self) -> int:
        if self.boxed:
            return max(4, round(self.font_size * part(self.look.box_padding)))
        return max(1, self.outline // 2)

    @property
    def gap(self) -> float:
        """The gap above the picture's text: past the box's padding, which once reached over
        it at 40% (the review of 2026-11-09)."""
        return max(GAP, round(part(self.look.box_padding) + GAP_PAST_PADDING, 4))

    @property
    def layout(self) -> str:
        """What a kept decision about where the subtitle goes depends on (render/placement.py,
        render/moments.py): another size, margin, padding or font is looked at again."""
        look = self.look
        return (f"{self.width}x{self.height}|{self.font}|{self.boxed}|{self.font_size}|"
                f"{self.usual_margin}|{self.top_margin}|{self.margin_h}|{self.shadow}|"
                f"{self.outline}|{look.position}")
