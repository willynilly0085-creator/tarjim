"""How well letters stand out from what is behind them (2026-11-09): the contrast ratio of
WCAG 2, against the box as it is drawn, its colour laid at its opacity over a white picture
and over a black one. A dark box is worst over white and a light box over black, so a pair
that passes over both passes on any frame."""
from tarjim.prefs.spec import colour_of

LEAST = 4.5  # WCAG AA for text
LINEAR_BELOW = 0.04045  # sRGB: darker channels are linear
Rgb = tuple[float, float, float]


def rgb(colour: str) -> Rgb:
    clean = colour_of(colour) or "#000000"
    return float(int(clean[1:3], 16)), float(int(clean[3:5], 16)), float(int(clean[5:7], 16))


def channel(value: float) -> float:
    part = value / 255
    return part / 12.92 if part <= LINEAR_BELOW else ((part + 0.055) / 1.055) ** 2.4


def luminance(colour: Rgb) -> float:
    red, green, blue = (channel(c) for c in colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(one: Rgb, other: Rgb) -> float:
    light, dark = sorted((luminance(one), luminance(other)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


WHITE, BLACK = 255.0, 0.0  # the two pictures a box is laid over


def over(colour: str, opacity: float, picture: float) -> Rgb:
    """The colour drawn at opacity percent over a grey picture (0 black, 255 white), as
    libass blends it."""
    share = opacity / 100
    red, green, blue = (share * c + (1 - share) * picture for c in rgb(colour))
    return red, green, blue


def stands_out(letters: str, behind: Rgb) -> bool:
    return ratio(rgb(letters), behind) >= LEAST
