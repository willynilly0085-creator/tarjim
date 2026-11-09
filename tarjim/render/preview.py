"""One real frame with the person's subtitle settings drawn on it (2026-11-09), for the page's
"شوف الشكل الحقيقي": the same subtitle file, mark and ffmpeg filter the burn uses, drawn by
libass, so the font it really picked and the way it really wraps are what the person sees.

The frame is tarjim's own sample picture (made by ffmpeg, light on one side and dark on the
other, so a box that only works on one of them shows it), or a moment of the person's video.
A still shows a line as it ends up: no fade, both speakers.
"""
import re
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from tarjim.languages import language
from tarjim.lines import display_lines
from tarjim.media import probe, run, source, tool
from tarjim.models import Cue, Word
from tarjim.prefs.model import Prefs
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.burn import PLAIN, drawing
from tarjim.render.fonts import usable
from tarjim.render.mark import with_mark
from tarjim.render.placement import chosen_place
from tarjim.render.room import fitted
from tarjim.rules import Rules, rules_for

WIDE, TALL = (1920, 1080), (1080, 1920)
SAMPLE = "gradients=s={w}x{h}:c0=0x1f2a33:c1=0xe2d6bd:x0=0:y0=0:x1={w}:y1=0:speed=0"
SAMPLES = {"ar": ("وش رايك نروح البحر بكرة الصبح؟", "فكرة حلوة، بس بدري"),
           "en": ("Shall we go to the beach tomorrow morning?", "Sounds good, but early")}
LONGEST_TEXT = 160
STILL = "still.jpg"
PICKED = re.compile(r"fontselect: \(([^,]+), \d+, \d+\) -> ([^,]+),")
SHOWN_AT = 0.0


@dataclass(frozen=True)
class Shot:
    video: Path | None = None  # None: tarjim's own sample picture
    at: float = 0.0  # seconds into the video
    portrait: bool = False  # the sample picture standing, as a phone video
    text: str = ""  # one line, or two speakers' lines as "a || b"; "" for the sample


@dataclass(frozen=True)
class Still:
    image: bytes  # JPEG
    width: int
    height: int
    font: str  # the face libass drew with, from its own log; "" when it did not say
    wraps: bool  # a line is longer than the picture holds, so libass wraps it


def spoken(text: str, target: str) -> list[str]:
    said = [" ".join(p.split()) for p in text[:LONGEST_TEXT].split("||")]
    lines = [p for p in said if p][:2]
    return lines or list(SAMPLES.get(target, SAMPLES["en"]))


def sample_cue(lines: list[str]) -> Cue:
    """Two speakers when there are two lines, the first one the main speaker."""
    parts = [[Word(w, SHOWN_AT, SHOWN_AT, who) for w in line.split()]
             for line, who in zip(lines, ("A", "B"), strict=False)]
    words = [w for part in parts for w in part]
    text = " || ".join(lines) if len(lines) > 1 else lines[0]
    return Cue(SHOWN_AT, 10.0, words, text, parts if len(parts) > 1 else [])


def drawn(prefs: Prefs, size: tuple[int, int], cue: Cue) -> tuple[str, Canvas, Rules]:
    look = replace(prefs.look, fade_ms=0)
    usual = language(prefs.target).font
    canvas = chosen_place([], Canvas.drawn(size, look, usable(look.font or usual, usual)))
    rules = fitted(rules_for(language(prefs.target), prefs), size[0], size[1], look)
    rules = replace(rules, staged=False)
    return render_ass([cue], canvas, rules), canvas, rules


def frame(shot: Shot) -> tuple[list[str], tuple[int, int]]:
    """ffmpeg's input for the shot, and the picture's size."""
    if shot.video is None:
        w, h = TALL if shot.portrait else WIDE
        return ["-f", "lavfi", "-i", SAMPLE.format(w=w, h=h)], (w, h)
    info = probe(shot.video)
    if not info.has_picture:
        raise ValueError("this file has no picture")
    at = min(max(0.0, shot.at), max(0.0, info.duration - 0.5))
    return ["-ss", f"{at:.3f}", *source(shot.video)], (info.width, info.height)


def still(prefs: Prefs, shot: Shot) -> Still:
    from tarjim.render.mark import mark_for

    given, size = frame(shot)
    cue = sample_cue(spoken(shot.text, prefs.target))
    subtitles, canvas, rules = drawn(prefs, size, cue)
    mark = mark_for(canvas)
    with tempfile.TemporaryDirectory(prefix="tarjim-preview-") as folder:
        (Path(folder) / PLAIN).write_text(with_mark(subtitles, mark), encoding="utf-8")
        done = run([tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "info", *given,
                    *drawing(mark), "-frames:v", "1", "-q:v", "2", STILL], cwd=Path(folder))
        made = Path(folder) / STILL
        if done.returncode != 0 or not made.is_file():
            raise RuntimeError("preview failed: " + done.stderr.strip()[-200:])
        image = made.read_bytes()
    wraps = any(len(line) > rules.line_chars for line in display_lines(cue.text, rules))
    return Still(image, size[0], size[1], picked(done.stderr, canvas.font), wraps)


def picked(log: str, font: str) -> str:
    """The face libass chose for the subtitle's font, from its fontselect line."""
    found = [got.strip() for asked, got in PICKED.findall(log)
             if asked.strip().lower() == font.lower()]
    return found[0] if found else ""
