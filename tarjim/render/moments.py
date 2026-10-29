"""Single lines moved off text the picture shows for a while only: an editor's note on a black
strip for a few seconds, a name caption, a slide. The video keeps its one place
(render/placement.py), which looks at 16 frames and counts text seen in at least 30% of them;
text up for 8 seconds of a 4-minute video is in about 3% of it, so that rightly leaves it out,
and tarjim's subtitle was drawn over it. Netflix's style guide moves a subtitle off burned-in
text for as long as the text shows, and so does this, line by line.

When text shows comes from every key frame of the video (render/timeline.py). A line moves when
a key frame inside it shows text where the subtitle is drawn. Key frames are seconds apart, so a
line with such a frame just before or after it, and none inside showing text, is decided by the
exact frame just inside its start or its end. That look decodes from the key frame before it,
so it costs up to one key frame's spacing; only lines beside text take one, and all of them
together get frames.BUDGET seconds. A look that could not be had moves the line anyway: moved
for nothing, a line stays readable; left in place, it covers the text.

A moved line goes where the video's place would go for that text: just above it, or to the top
when that passes the middle, clear of tarjim's mark when the mark is at the top. A video whose
subtitle is already at the top moves no line. What was seen is kept in the job's folder, and
looking never fails a job."""
import json
from bisect import bisect_left, bisect_right
from dataclasses import replace
from pathlib import Path

from tarjim.job import Job, checkpoint
from tarjim.models import Cue
from tarjim.render import frames, timeline
from tarjim.render.ass import Canvas, Move
from tarjim.render.mark import Mark
from tarjim.render.placement import MIDDLE, meets, place, size
from tarjim.render.text_bands import Band, frame_bands
from tarjim.render.timeline import Seen

KEPT = "moments.json"
# A key frame further than this from a line says nothing about it.
NEAR = 10.0
# An exact look this far inside the line, past its fade in or before its fade out.
EDGE = 0.1


def hit(bands: list[Band], canvas: Canvas) -> bool:
    """Whether any of these bands meets the subtitle in the video's place."""
    block, _gap = size(canvas)
    bottom = canvas.height - canvas.margin_v
    return any(meets(band, canvas, bottom - block, bottom) for band in bands)


def neighbours(seen: Seen, cue: Cue) -> list[tuple[float, float]]:
    """(the nearest frame before the line, where to look inside its start), and the same for
    the nearest frame after it and its end."""
    times = sorted(seen)
    first, past = bisect_left(times, cue.start), bisect_right(times, cue.end)
    edge = min(EDGE, (cue.end - cue.start) / 2)
    before = [(t, round(cue.start + edge, 3)) for t in times[max(0, first - 1):first]
              if t >= cue.start - NEAR]
    after = [(t, round(cue.end - edge, 3)) for t in times[past:past + 1] if t <= cue.end + NEAR]
    return before + after


def wanted(seen: Seen, cues: list[Cue], canvas: Canvas) -> list[float]:
    """The exact looks the lines need: inside each line, beside a frame showing text there."""
    looks = {look for cue in cues for near, look in neighbours(seen, cue)
             if hit(seen[near], canvas)}
    return sorted(looks - set(seen))


def evidence(seen: Seen, cue: Cue, canvas: Canvas) -> list[Band]:
    """Every band of the frames that show text where the line would be drawn."""
    showing = [seen[t] for t in seen if cue.start <= t <= cue.end and hit(seen[t], canvas)]
    if not showing:  # a look that could not be had: the frame beside it stands in for it
        showing = [seen[near] for near, look in neighbours(seen, cue)
                   if look not in seen and hit(seen[near], canvas)]
    return [band for bands in showing for band in bands]


def mark_band(mark: Mark | None, canvas: Canvas) -> list[Band]:
    """The mark's rows, when it is at the top, where a moved line may go."""
    if mark is None or mark.y >= canvas.height * MIDDLE:
        return []
    return [(mark.y / canvas.height, (mark.y + mark.logo) / canvas.height)]


def decide(seen: Seen, cues: list[Cue], canvas: Canvas, mark: Mark | None) -> tuple[Move, ...]:
    moves = []
    for cue in cues:
        found = evidence(seen, cue, canvas)
        if not found:
            continue
        spot = place([*found, *canvas.bands, *mark_band(mark, canvas)], canvas)
        if spot != canvas:
            moves.append((cue.start, cue.end, spot.margin_v, spot.top))
    return tuple(moves)


def kept(record: Path) -> Seen | None:
    if not record.is_file():
        return None
    data = json.loads(record.read_text(encoding="utf-8"))
    return {float(at): [(float(t), float(b)) for t, b in bands] for at, bands in data["seen"]}


def keep(record: Path, seen: Seen) -> None:
    rows = [[at, [[round(t, 4), round(b, 4)] for t, b in seen[at]]] for at in sorted(seen)]
    record.write_text(json.dumps({"seen": rows}), encoding="utf-8")


def looked(video: Path, moments: list[float]) -> Seen:
    taken = frames.within_budget(moments, lambda at, limit: frames.exact(video, at, limit))
    return {at: frame_bands(f) for at, f in zip(moments, taken, strict=True) if f is not None}


def observed(job: Job, cues: list[Cue], canvas: Canvas) -> Seen:
    seen = kept(job.cache / KEPT)
    if seen is None:
        seen = timeline.scan(job.video, (canvas.width, canvas.height), cues[-1].end)
    return seen | looked(job.video, wanted(seen, cues, canvas))


def moved(job: Job, cues: list[Cue], canvas: Canvas, mark: Mark | None) -> Canvas:
    """The canvas with the lines that would cover the picture's passing text moved off it."""
    spoken = [cue for cue in cues if cue.text.strip()]
    if canvas.top or not spoken:
        return canvas
    try:
        seen = observed(job, spoken, canvas)
    except Exception:  # anything that goes wrong while looking moves no line
        return canvas
    checkpoint()  # a cancel while looking: the job stops, and what was half seen is not kept
    try:
        if seen:
            keep(job.cache / KEPT, seen)
        return replace(canvas, moves=decide(seen, spoken, canvas, mark))
    except Exception:
        return canvas
