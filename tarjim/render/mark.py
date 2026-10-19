"""tarjim's mark on every video it writes: its logo with @Cut_Code beside it, small, in a corner.

Sized from the picture like the subtitle. Landscape and square videos carry it bottom-left. A
portrait video carries it top-left and a little larger: the apps that show portrait videos print
the account name and caption over the bottom-left, and size it from the width so it stays legible.

It never sits on tarjim's subtitle. Under a subtitle at the same edge it moves nearer the edge;
when that leaves too little room, or the picture's own text (render/placement.py) is at that
edge, it goes to the other edge. The text is drawn by libass from the burn's .ass file and the
logo by ffmpeg in the same pass (render/burn.py); the .srt and .ass files handed out carry none."""
from dataclasses import dataclass
from pathlib import Path

from tarjim.config import setting
from tarjim.render.ass import Canvas
from tarjim.render.placement import size
from tarjim.render.timecode import ass_time

LOGO = Path(__file__).with_name("mark.png")
HANDLE = "@Cut_Code"
FONT = "Segoe UI"
LANDSCAPE_LOGO = 0.045
PORTRAIT_LOGO = 0.06
TEXT = 0.52
MARGIN = 0.028
# The least room between the mark and the picture's edge, as a share of the usual margin.
FLOOR = 0.4
SPACE = 0.22
LOGO_OPACITY = 0.85
# 85% opaque white letters with a thin, half-clear dark edge.
STYLE = ("Style: Mark,{font},{size},&H26FFFFFF,&H26FFFFFF,&H70101010,&HA0000000,-1,0,0,0,"
         "100,100,0,0,1,{outline},{shadow},4,0,0,0,1")
WHOLE_VIDEO = ass_time(24 * 3600.0)


@dataclass(frozen=True)
class Mark:
    """Where the logo goes (its top-left corner) and how tall it is; the text follows it."""
    x: int
    y: int
    logo: int

    @property
    def text_size(self) -> int:
        return round(self.logo * TEXT)

    @property
    def text_x(self) -> int:
        return self.x + self.logo + round(self.logo * SPACE)


def wanted() -> bool:
    return setting("video_mark") != "no"


def logo_size(canvas: Canvas) -> int:
    if canvas.portrait:
        return round(canvas.width * PORTRAIT_LOGO)
    return round(min(canvas.width, canvas.height) * LANDSCAPE_LOGO)


def margin(canvas: Canvas) -> int:
    return round(min(canvas.width, canvas.height) * MARGIN)


def stroke(canvas: Canvas) -> int:
    """How far the subtitle's outline and shadow, or its box, reach past its lines."""
    return canvas.shadow if canvas.bright else canvas.outline + canvas.shadow


def room(canvas: Canvas, top: bool) -> int:
    """Rows between that edge of the picture and tarjim's subtitle."""
    block, _gap = size(canvas)
    if top == canvas.top:
        return canvas.margin_v - stroke(canvas)
    return canvas.height - canvas.margin_v - block - stroke(canvas)


def at_edge(canvas: Canvas, top: bool) -> Mark | None:
    logo, usual = logo_size(canvas), margin(canvas)
    gap = min(usual, room(canvas, top) - logo)
    if gap < usual * FLOOR:
        return None
    return Mark(usual, gap if top else canvas.height - gap - logo, logo)


def covered(mark: Mark, canvas: Canvas) -> bool:
    height = canvas.height
    return any(t * height < mark.y + mark.logo and b * height > mark.y for t, b in canvas.bands)


def place_mark(canvas: Canvas) -> Mark:
    """The usual edge when it is free, else the other; clear of the subtitle before anything."""
    fits = [m for m in (at_edge(canvas, top) for top in (canvas.portrait, not canvas.portrait))
            if m is not None]
    free = [m for m in fits if not covered(m, canvas)]
    usual, logo = margin(canvas), logo_size(canvas)
    fallback = Mark(usual, usual if canvas.portrait else canvas.height - usual - logo, logo)
    return (free or fits or [fallback])[0]


def mark_for(canvas: Canvas) -> Mark | None:
    """The mark for this picture, or None when the person turned it off in Settings."""
    return place_mark(canvas) if wanted() else None


def with_mark(ass: str, mark: Mark | None) -> str:
    """The subtitles with the mark's text added on a layer of its own."""
    if mark is None:
        return ass
    head, events = ass.split("\n\n[Events]\n", 1)
    edge = max(1, round(mark.text_size / 22))
    style = STYLE.format(font=FONT, size=mark.text_size, outline=edge, shadow=edge)
    line = (f"Dialogue: 1,{ass_time(0.0)},{WHOLE_VIDEO},Mark,,0,0,0,,"
            f"{{\\pos({mark.text_x},{mark.y + mark.logo // 2})}}{HANDLE}")
    return f"{head}\n{style}\n\n[Events]\n{events}{line}\n"


def overlay(mark: Mark, picture: str) -> str:
    """The filter that lays the logo (ffmpeg's second input) over the labelled picture."""
    return (f"[1:v]scale={mark.logo}:{mark.logo}:flags=lanczos,format=rgba,"
            f"colorchannelmixer=aa={LOGO_OPACITY}[logo];"
            f"[{picture}][logo]overlay={mark.x}:{mark.y}:format=auto")
