"""A small picture is enlarged before the subtitles are drawn on it, so the letters stay sharp.

libass draws at the size of the picture it is given. On a 464-line download each letter had
about twenty rows of pixels, and a phone or a TV enlarging the video blurred them (the owner,
2026-10-31: the writing gets weaker when the video is weak). So the picture is first enlarged
to fit 1920×1080 (lanczos) and the subtitles are drawn on that. Their layout does not change:
the .ass file places everything in its own PlayRes coordinates, which libass maps onto whatever
picture it gets, outline and shadow included (ScaledBorderAndShadow), but each letter now has two
to five times the rows. The picture gains no detail and loses none; the rate it may spend grows
with its size (burn.encode), and tarjim's logo, laid on in pixels, grows with it.
"""
import re
from dataclasses import dataclass

from tarjim.render.mark import Mark

WIDEST, TALLEST = 1920, 1080  # one 1080p frame, either way round
LEAST = 1.1  # enlarging by less than this sharpens nothing worth the bigger file
PLAY_RES = re.compile(r"^PlayRes([XY]):\s*(\d+)", re.MULTILINE)


@dataclass(frozen=True)
class Enlarged:
    width: int
    height: int
    factor: float


def even(value: float) -> int:
    return max(2, 2 * round(value / 2))


def drawn_size(ass: str) -> tuple[int, int]:
    """The picture size the .ass file was laid out for (its PlayRes); 0 when it says none."""
    found = dict(PLAY_RES.findall(ass))
    return int(found.get("X", 0)), int(found.get("Y", 0))


def enlarged(size: tuple[int, int]) -> Enlarged | None:
    """The size to draw at, or None when the picture is already large enough."""
    width, height = size
    if width <= 0 or height <= 0:
        return None
    box = (WIDEST, TALLEST) if width >= height else (TALLEST, WIDEST)
    factor = min(box[0] / width, box[1] / height)
    if factor < LEAST:
        return None
    return Enlarged(even(width * factor), even(height * factor), factor)


def grown(mark: Mark, by: Enlarged | None) -> Mark:
    """The logo's place and size on the enlarged picture."""
    if by is None:
        return mark
    return Mark(round(mark.x * by.factor), round(mark.y * by.factor),
                round(mark.logo * by.factor))


def scale_filter(by: Enlarged | None) -> str:
    return f"scale={by.width}:{by.height}:flags=lanczos," if by else ""
