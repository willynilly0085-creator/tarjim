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
from dataclasses import dataclass, replace

from tarjim.render.mark import Mark

WIDEST, TALLEST = 1920, 1080  # one 1080p frame, either way round
# What the person may enlarge to (output.enlarge, 2026-11-09): its frame, or nothing.
FRAMES = {"1080": (WIDEST, TALLEST), "720": (1280, 720), "off": (0, 0)}
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


def enlarged(size: tuple[int, int], frame: str = "1080") -> Enlarged | None:
    """The size to draw at, or None when the picture is already large enough or the person
    keeps every picture at its own size."""
    width, height = size
    wide, tall = FRAMES.get(frame, (WIDEST, TALLEST))
    if width <= 0 or height <= 0 or not wide:
        return None
    box = (wide, tall) if width >= height else (tall, wide)
    factor = min(box[0] / width, box[1] / height)
    if factor < LEAST:
        return None
    return Enlarged(even(width * factor), even(height * factor), factor)


def grown(mark: Mark, by: Enlarged | None) -> Mark:
    """The logo's place and size on the enlarged picture."""
    if by is None:
        return mark
    return replace(mark, x=round(mark.x * by.factor), y=round(mark.y * by.factor),
                   logo=round(mark.logo * by.factor))


def scale_filter(by: Enlarged | None) -> str:
    return f"scale={by.width}:{by.height}:flags=lanczos," if by else ""
