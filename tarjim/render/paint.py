"""The person's colours and opacities as libass writes them (2026-11-09).

ASS colours are &HAABBGGRR, with the alpha byte counting how clear a colour is (0 opaque, 255
gone). An opacity is laid on in proportion to the one tarjim drew before, so each default gives
the byte it always had: the box's 69% is &H50, the shadow's 45% is &H8C, the mark's 85% &H26.
"""
from tarjim.prefs.spec import colour_of

CLEAR = 255
FULL = 100


def bgr(colour: str) -> str:
    clean = colour_of(colour) or "#000000"
    return f"{clean[5:7]}{clean[3:5]}{clean[1:3]}"


def ass_colour(colour: str, alpha: int = 0) -> str:
    """A style's colour: &HAABBGGRR."""
    return f"&H{alpha:02X}{bgr(colour)}"


def tag_colour(colour: str) -> str:
    """A colour inside a line's own tag (\\c&HBBGGRR&)."""
    return f"&H{bgr(colour)}&"


def alpha_at(opacity: float, usual: float, usual_alpha: int) -> int:
    """The alpha byte of opacity percent, drawn as much more or less seen than at the usual
    opacity, whose byte it keeps exactly."""
    if opacity >= FULL:
        return 0
    seen = (CLEAR - usual_alpha) * opacity / usual
    return min(CLEAR, max(0, CLEAR - round(seen)))
