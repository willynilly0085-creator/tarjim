"""Where tarjim's subtitle goes when the picture already carries text there.

One place for the whole video, so the subtitle never jumps from line to line: in its usual place
when that is clear; lifted to sit just above the picture's text when that is not; at the top when
lifting would take it past the middle of the picture; in its usual place again when the top is
taken as well. The size never changes, and a portrait video keeps its larger bottom margin (the
apps' buttons sit there), so a lifted subtitle only ever moves up from it.

Looking is a few seconds at most and never fails a job: when anything goes wrong the subtitle
keeps its usual place. The decision is kept in the job's folder, and a re-run reuses it."""
import json
import time
from dataclasses import replace
from pathlib import Path

from tarjim.job import Job
from tarjim.models import Cue
from tarjim.render import frames
from tarjim.render.ass import Canvas
from tarjim.render.text_bands import Band, text_bands

LINE = 1.3
LINES = 2
GAP = 0.3
MIDDLE = 0.5
TOP_SAFE = {False: 0.05, True: 0.12}
KEPT = "placement.json"


def size(canvas: Canvas) -> tuple[int, int]:
    """How tall two lines of subtitle are, and the gap kept between them and other text."""
    return round(LINES * LINE * canvas.font_size), round(GAP * canvas.font_size)


def meets(band: Band, canvas: Canvas, upper: int, lower: int) -> bool:
    """Whether the band crosses the rows from upper to lower, gap included."""
    _block, gap = size(canvas)
    height = canvas.height
    return band[0] * height < lower + gap and band[1] * height > upper - gap


def clear_bottom(bands: list[Band], canvas: Canvas) -> int:
    block, gap = size(canvas)
    margin, height = canvas.margin_v, canvas.height
    for band in sorted(bands, key=lambda b: -b[1]):
        if meets(band, canvas, height - margin - block, height - margin):
            margin = round(height - band[0] * height + gap)
    return margin


def clear_top(bands: list[Band], canvas: Canvas) -> int:
    block, gap = size(canvas)
    margin = round(canvas.height * TOP_SAFE[canvas.portrait])
    for band in sorted(bands):
        if meets(band, canvas, margin, margin + block):
            margin = round(band[1] * canvas.height + gap)
    return margin


def place(bands: list[Band], canvas: Canvas) -> Canvas:
    block, _gap = size(canvas)
    middle = canvas.height * MIDDLE
    lifted = clear_bottom(bands, canvas)
    if lifted == canvas.margin_v:
        return canvas
    if canvas.height - lifted - block >= middle:
        return replace(canvas, margin=lifted)
    top = clear_top(bands, canvas)
    return replace(canvas, margin=top, top=True) if top + block <= middle else canvas


def look(video: Path, cues: list[Cue], duration: float) -> list[Band]:
    return text_bands(frames.sample(video, frames.sample_times(cues, duration)))


def kept(record: Path, canvas: Canvas) -> Canvas | None:
    if not record.is_file():
        return None
    data = json.loads(record.read_text(encoding="utf-8"))
    margin, top = data["margin"], data["top"]
    if not isinstance(margin, int) or not 0 <= margin < canvas.height:
        return None
    usual = margin == canvas.margin_v and not top
    chosen = canvas if usual else replace(canvas, margin=margin, top=bool(top))
    return replace(chosen, bands=tuple((float(t), float(b)) for t, b in data["bands"]))


def placed(job: Job, cues: list[Cue], canvas: Canvas, duration: float) -> Canvas:
    record = job.cache / KEPT
    # Anything at all that goes wrong while looking leaves the subtitle in its usual place.
    try:
        reused = kept(record, canvas)
        if reused is not None:
            return reused
        began = time.perf_counter()
        bands = look(job.video, cues, duration)
        chosen = replace(place(bands, canvas), bands=tuple(bands))
        record.write_text(json.dumps({
            "bands": [[round(t, 4), round(b, 4)] for t, b in bands], "top": chosen.top,
            "margin": chosen.margin_v, "seconds": round(time.perf_counter() - began, 2)}),
            encoding="utf-8")
    except Exception:
        return canvas
    return chosen
