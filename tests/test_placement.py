"""Where the picture already carries text, tarjim's subtitle goes somewhere else. The clips are
made here: a moving test pattern, with and without a caption drawn into it."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tarjim.job import Job
from tarjim.models import Cue
from tarjim.render import frames, placement
from tarjim.render.ass import Canvas, render_ass

FONTS = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"]
WORDS = ["he has been sad", "ever since then", "poor guy really", "we all know it"]
SPEECH = [Cue(0.3 + i, 1.0 + i, text="كلام") for i in range(8)]


def font(folder: Path) -> Path:
    found = next((Path(f) for f in FONTS if Path(f).is_file()), None)
    if found is None:
        pytest.skip("no font for drawtext on this computer")
    return Path(shutil.copyfile(found, folder / f"font{found.suffix}"))


def caption(at: float, size: int) -> list[str]:
    """Words drawn light with a dark edge, as creators burn them, changing every two seconds."""
    return [f"drawtext=fontfile={'{font}'}:text='{text}':fontsize={size}:fontcolor=white:"
            f"borderw=3:bordercolor=black:x=(w-tw)/2:y=h*{at}:"
            f"enable='between(t,{2 * i},{2 * i + 2})'" for i, text in enumerate(WORDS)]


def clip(folder: Path, shape: tuple[int, int], rows: list[float]) -> Path:
    width, height = shape
    face = font(folder).name
    drawn = [d.replace("{font}", face) for at in rows
             for d in caption(at, min(width, height) // 13)]
    target = folder / f"clip-{width}x{height}-{len(rows)}-{rows[0] if rows else 0}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"testsrc2=size={width}x{height}:rate=10:duration=8",
                    "-vf", ",".join(drawn) or "null", "-c:v", "libx264", "-g", "10",
                    "-pix_fmt", "yuv420p", target.name], check=True, cwd=folder)
    return target


def placed(folder: Path, video: Path) -> Canvas:
    job = Job(video, cache_dir=folder / "cache")
    width, height = (int(n) for n in video.stem.split("-")[1].split("x"))
    return placement.placed(job, SPEECH, Canvas(width, height), 8.0)


def bottom_of(canvas: Canvas) -> int:
    return canvas.height - canvas.margin_v


def test_a_caption_at_the_bottom_lifts_the_subtitle_just_above_it(tmp_path: Path) -> None:
    canvas = placed(tmp_path, clip(tmp_path, (640, 360), [0.8]))
    default = Canvas(640, 360)
    assert not canvas.top
    assert canvas.margin_v > default.margin_v
    assert bottom_of(canvas) <= 0.8 * 360
    assert bottom_of(canvas) >= 0.8 * 360 - 2 * default.font_size
    assert f",2,38,38,{canvas.margin_v}," in render_ass([], canvas)


def test_text_at_the_top_leaves_the_subtitle_where_it_was(tmp_path: Path) -> None:
    assert placed(tmp_path, clip(tmp_path, (640, 360), [0.05])) == Canvas(640, 360)


def test_a_picture_without_text_leaves_the_subtitle_where_it_was(tmp_path: Path) -> None:
    assert placed(tmp_path, clip(tmp_path, (640, 360), [])) == Canvas(640, 360)


def test_a_portrait_caption_lifts_the_subtitle_and_stays_off_the_bottom(tmp_path: Path) -> None:
    canvas = placed(tmp_path, clip(tmp_path, (360, 640), [0.74]))
    assert not canvas.top
    assert bottom_of(canvas) <= 0.74 * 640
    assert canvas.margin_v > Canvas(360, 640).margin_v


def test_text_up_to_the_middle_sends_the_subtitle_to_the_top(tmp_path: Path) -> None:
    canvas = placed(tmp_path, clip(tmp_path, (640, 360), [0.8, 0.62]))
    assert canvas.top
    assert canvas.margin_v == round(360 * placement.TOP_SAFE[False])
    assert f",8,38,38,{canvas.margin_v}," in render_ass([], canvas)


def test_a_file_that_cannot_be_decoded_keeps_todays_place(tmp_path: Path) -> None:
    broken = tmp_path / "clip-640x360-1-0.8.mp4"
    broken.write_bytes(b"not a video at all")
    assert placed(tmp_path, broken) == Canvas(640, 360)
    assert not (tmp_path / "cache" / broken.stem / placement.KEPT).exists()


def test_a_failure_while_looking_keeps_todays_place(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_video: Path, _at: float, _limit: float = 0) -> None:
        raise OSError("ffmpeg vanished")

    monkeypatch.setattr(frames, "grab", broken)
    assert placed(tmp_path, clip(tmp_path, (640, 360), [0.8])) == Canvas(640, 360)


def test_a_rerun_reuses_the_kept_decision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = clip(tmp_path, (640, 360), [0.8])
    first = placed(tmp_path, video)
    kept = json.loads((tmp_path / "cache" / video.stem / placement.KEPT).read_text("utf-8"))
    assert kept["margin"] == first.margin_v and kept["bands"]

    def never(_video: Path, _at: float, _limit: float = 0) -> None:
        raise AssertionError("looked at the picture again")

    monkeypatch.setattr(frames, "grab", never)
    assert placed(tmp_path, video) == first


def test_bands_clear_of_the_subtitle_change_nothing() -> None:
    canvas = Canvas(1920, 1080)
    assert placement.place([(0.02, 0.08), (0.96, 0.99)], canvas) == canvas


def test_a_band_over_the_subtitle_lifts_it_above_with_a_gap() -> None:
    lifted = placement.place([(0.86, 0.93)], Canvas(1920, 1080))
    assert not lifted.top
    assert 1080 * 0.86 - 40 <= bottom_of(lifted) < 1080 * 0.86


def test_when_both_halves_carry_text_the_subtitle_stays_where_it_was() -> None:
    canvas = Canvas(1920, 1080)
    assert placement.place([(0.05, 0.45), (0.55, 0.93)], canvas) == canvas


def test_the_spoken_moments_are_where_frames_are_taken() -> None:
    times = frames.sample_times(SPEECH, 8.0)
    assert times == [0.65 + i for i in range(8)]
    assert len(frames.sample_times([], 600.0)) == frames.MOST
    many = [Cue(i, i + 1.0, text="x") for i in range(100)]
    assert len(frames.sample_times(many, 100.0)) == frames.MOST
    order = frames.spread(list(range(16)))
    assert sorted(order) == list(range(16)) and order[:4] == [0, 4, 8, 12]


def test_looking_stops_at_the_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np

    calls: list[float] = []

    def slow(_video: Path, at: float, _limit: float = 0) -> np.ndarray:
        calls.append(at)
        frames.time.sleep(0.2)
        return np.full((4, frames.WIDTH), len(calls), np.uint8)

    monkeypatch.setattr(frames, "grab", slow)
    monkeypatch.setattr(frames, "BUDGET", 0.3)
    assert len(frames.sample(tmp_path / "v.mp4", [float(i) for i in range(16)])) < 16
