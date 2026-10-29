"""Text the picture shows for a while only (an editor's note on a black strip for a few seconds)
keeps the subtitle's one place for the video, and moves just the lines said while it shows. The
clip is made here: a moving test pattern with a key frame every two seconds and a note drawn
over the bottom from 8.5 s to 12.5 s, between key frames on both sides."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tarjim.job import CHECKPOINT, Job
from tarjim.models import Cue
from tarjim.render import frames, moments, placement, timeline
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.mark import Mark
from tests.test_placement import font

CUES = [Cue(0.3 + i, 1.0 + i, text="كلام") for i in range(20)]
NOTE = ("he has been sad ever since", "poor guy, we all know it")


def noted(folder: Path) -> Path:
    face = font(folder).name
    shown = "enable='between(t,8.5,12.5)'"
    drawn = [f"drawbox=y=ih*0.76:w=iw:h=ih*0.22:color=black:t=fill:{shown}"] + [
        f"drawtext=fontfile={face}:text='{text}':fontsize=22:fontcolor=white:"
        f"x=(w-tw)/2:y=h*{at}:{shown}" for at, text in zip((0.8, 0.89), NOTE, strict=True)]
    target = folder / "noted.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=640x360:rate=10:duration=20", "-vf", ",".join(drawn),
                    "-c:v", "mpeg4", "-g", "20", "-pix_fmt", "yuv420p", target.name],
                   check=True, cwd=folder)
    return target


def look(folder: Path, video: Path, mark: Mark | None = None) -> Canvas:
    job = Job(video, cache_dir=folder / "cache")
    canvas = placement.placed(job, CUES, Canvas(640, 360), 20.0)
    return moments.moved(job, CUES, canvas, mark)


def moved_lines(canvas: Canvas) -> list[int]:
    return [round(start - 0.3) for start, _end, _margin, _top in canvas.moves]


def test_only_the_lines_said_over_the_note_move(tmp_path: Path) -> None:
    canvas = look(tmp_path, noted(tmp_path))
    usual = Canvas(640, 360)
    assert canvas.margin_v == usual.margin_v and not canvas.top  # the video keeps its place
    assert moved_lines(canvas) == [8, 9, 10, 11, 12]
    for _start, _end, margin, top in canvas.moves:
        assert not top and margin > usual.margin_v
        assert 360 - margin <= 0.8 * 360  # the subtitle's bottom sits above the note's first line


def test_a_moved_line_carries_its_own_place_in_the_subtitle_file() -> None:
    canvas = Canvas(1920, 1080, moves=((1.0, 2.0, 333, False), (3.0, 4.0, 54, True)))
    cues = [Cue(1.0, 2.0, text="فوق الملاحظة"), Cue(3.0, 4.0, text="في الأعلى"),
            Cue(5.0, 6.0, text="مكانه")]
    events = [line for line in render_ass(cues, canvas).splitlines() if line.startswith("Dia")]
    assert ",Default,,0,0,333,,{\\fad" in events[0]
    assert ",Default,,0,0,54,,{\\an8}{\\fad" in events[1]
    assert ",Default,,0,0,0,,{\\fad" in events[2]


def test_a_rerun_reuses_what_was_seen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = noted(tmp_path)
    first = look(tmp_path, video)
    kept = json.loads((tmp_path / "cache" / video.stem / moments.KEPT).read_text("utf-8"))
    assert kept["seen"]

    def never(*_args: object) -> None:
        raise AssertionError("looked at the picture again")

    monkeypatch.setattr(timeline, "scan", never)
    monkeypatch.setattr(frames, "grab", never)
    assert look(tmp_path, video).moves == first.moves


def test_a_failure_while_looking_moves_nothing(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object) -> None:
        raise OSError("ffmpeg vanished")

    monkeypatch.setattr(timeline, "scan", broken)
    assert look(tmp_path, noted(tmp_path)).moves == ()


def test_a_cancel_while_looking_still_cancels(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    class Stopped(Exception):
        pass

    def stop() -> None:
        raise Stopped

    monkeypatch.setattr(timeline, "scan", lambda *_args: {})
    token = CHECKPOINT.set(stop)
    try:
        with pytest.raises(Stopped):
            moments.moved(Job(tmp_path / "v.mp4", cache_dir=tmp_path), CUES, Canvas(640, 360),
                          None)
    finally:
        CHECKPOINT.reset(token)


def test_a_missing_exact_look_moves_the_line_rather_than_cover_the_text() -> None:
    seen = {0.0: [], 3.0: [(0.86, 0.93)], 6.0: []}
    cues = [Cue(1.0, 2.0, text="x"), Cue(3.5, 4.5, text="x")]
    canvas = Canvas(1920, 1080)
    assert moments.wanted(seen, cues, canvas) == [1.9, 3.6]
    moved = moments.decide(seen, cues, canvas, None)
    assert [m[:2] for m in moved] == [(1.0, 2.0), (3.5, 4.5)]
    seen |= {1.9: [], 3.6: []}  # looked: the note came after the first line, left before the next
    assert moments.decide(seen, cues, canvas, None) == ()


def test_text_far_from_a_line_is_not_looked_for() -> None:
    seen = {0.0: [(0.86, 0.93)], 30.0: []}
    assert moments.wanted(seen, [Cue(20.0, 21.0, text="x")], Canvas(1920, 1080)) == []


def test_a_line_sent_to_the_top_keeps_clear_of_the_mark_there() -> None:
    canvas = Canvas(1920, 1080)
    mark = Mark(30, 30, 49)
    moved = moments.decide({1.0: [(0.6, 0.96)]}, [Cue(0.5, 1.5, text="x")], canvas, mark)
    (_start, _end, margin, top), = moved
    assert top and margin >= 30 + 49


def test_a_video_already_at_the_top_moves_no_line(tmp_path: Path) -> None:
    canvas = Canvas(640, 360, margin=18, top=True)
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path)
    assert moments.moved(job, CUES, canvas, None) == canvas


def test_the_budget_grows_with_the_video_and_stays_bounded() -> None:
    assert timeline.budget(60.0) == timeline.SHORTEST
    assert timeline.budget(1800.0) == pytest.approx(18.0)
    assert timeline.budget(3600.0) == timeline.LONGEST
    assert timeline.budget(6 * 3600.0) == timeline.LONGEST


def test_reading_stops_at_the_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    endless = ("import sys, time\n"
               "while True:\n"
               f"    sys.stdout.buffer.write(bytes({timeline.WIDTH * 270})); sys.stdout.flush()\n"
               "    time.sleep(0.05)\n")
    monkeypatch.setattr(timeline, "command", lambda *_args: [sys.executable, "-c", endless])
    monkeypatch.setattr(timeline, "budget", lambda _length: 0.5)
    began = time.monotonic()
    assert timeline.scan(tmp_path / "v.mp4", (1920, 1080), 3600.0) == {}
    assert time.monotonic() - began < 3.0


def test_the_scan_reads_key_frames_only_with_their_times(tmp_path: Path) -> None:
    seen = timeline.scan(noted(tmp_path), (640, 360), 20.0)
    assert sorted(seen) == [float(t) for t in range(0, 20, 2)]
    assert [t for t, bands in seen.items() if bands] == [10.0, 12.0]
