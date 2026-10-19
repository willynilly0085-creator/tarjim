"""tarjim's mark (its logo and @Cut_Code) on every video it writes, in a corner that keeps clear of
the subtitle and of text already in the picture; never in the .srt or .ass files handed out."""
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tarjim import media, pipeline
from tarjim.job import Job
from tarjim.models import Cue
from tarjim.render import burn, mark
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.placement import size

CUES = [Cue(0.5, 2.0, text="مرحبا يا جماعة"), Cue(2.5, 4.0, text="كيف الحال")]


def rows(canvas: Canvas) -> tuple[int, int]:
    """The rows tarjim's subtitle can reach, its outline and shadow included."""
    block, _gap = size(canvas)
    edge = mark.stroke(canvas)
    if canvas.top:
        return canvas.margin_v - edge, canvas.margin_v + block + edge
    return canvas.height - canvas.margin_v - block - edge, canvas.height - canvas.margin_v + edge


def clear(placed: mark.Mark, canvas: Canvas) -> bool:
    upper, lower = rows(canvas)
    return placed.y + placed.logo <= upper or placed.y >= lower


def test_landscape_carries_the_mark_bottom_left() -> None:
    canvas = Canvas(1920, 1080)
    placed = mark.place_mark(canvas)
    assert placed.logo == round(1080 * 0.045) and placed.x == round(1080 * 0.028)
    assert placed.y > 1080 * 0.85 and clear(placed, canvas)
    assert 0.45 <= placed.text_size / placed.logo <= 0.6


def test_a_square_video_is_treated_like_a_landscape_one() -> None:
    placed = mark.place_mark(Canvas(1080, 1080))
    assert placed.y > 1080 * 0.85 and placed.x == round(1080 * 0.028)


def test_portrait_carries_a_larger_mark_top_left() -> None:
    canvas = Canvas(608, 1080)
    placed = mark.place_mark(canvas)
    assert placed.logo == 36 and placed.x == round(608 * 0.028) == placed.y
    landscape = mark.place_mark(Canvas(1080, 608))
    assert placed.logo > landscape.logo


def test_the_burned_ass_carries_the_mark_style_and_event_where_the_logo_is() -> None:
    canvas = Canvas(608, 1080)
    placed = mark.place_mark(canvas)
    ass = mark.with_mark(render_ass(CUES, canvas), placed)
    styles = [line for line in ass.splitlines() if line.startswith("Style: Mark,")]
    events = [line for line in ass.splitlines() if ",Mark,," in line]
    assert len(styles) == 1 and len(events) == 1
    assert ",4,0,0,0,1" in styles[0] and ",-1,0,0,0," in styles[0]
    middle = placed.y + placed.logo // 2
    assert events[0].startswith("Dialogue: 1,0:00:00.00,")
    assert placed.x + placed.logo < placed.text_x < placed.x + 1.5 * placed.logo
    assert events[0].endswith(f"{{\\pos({placed.text_x},{middle})}}@Cut_Code")
    assert ass.index("[Events]") > ass.index("Style: Mark,") > ass.index("Style: Default,")
    assert mark.with_mark(render_ass(CUES, canvas), None) == render_ass(CUES, canvas)


def test_a_subtitle_at_the_top_of_a_portrait_video_never_meets_the_mark() -> None:
    usual = Canvas(608, 1080, margin=130, top=True)
    assert mark.place_mark(usual).y < 540 and clear(mark.place_mark(usual), usual)
    high = Canvas(608, 1080, margin=30, top=True)
    moved = mark.place_mark(high)
    assert moved.y > 540 and clear(moved, high)


@pytest.mark.parametrize("canvas", [
    Canvas(1920, 1080), Canvas(1280, 720, bright=True), Canvas(1080, 1080), Canvas(1440, 1080),
    Canvas(640, 360), Canvas(1920, 1080, margin=54, top=True), Canvas(1080, 1920),
    Canvas(608, 1080, margin=300), Canvas(1440, 2560, margin=40, top=True)])
def test_the_mark_never_sits_on_the_subtitle(canvas: Canvas) -> None:
    assert clear(mark.place_mark(canvas), canvas)


def test_text_already_in_the_marks_corner_sends_it_to_the_other_edge() -> None:
    landscape = mark.place_mark(Canvas(1920, 1080, bands=((0.9, 0.99),)))
    assert landscape.y < 540
    portrait = mark.place_mark(Canvas(608, 1080, bands=((0.0, 0.06),)))
    assert portrait.y > 540 and clear(portrait, Canvas(608, 1080))
    elsewhere = mark.place_mark(Canvas(1920, 1080, bands=((0.4, 0.5),)))
    assert elsewhere == mark.place_mark(Canvas(1920, 1080))


def test_the_setting_turns_the_mark_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARJIM_VIDEO_MARK", "no")
    assert mark.mark_for(Canvas(1920, 1080)) is None
    monkeypatch.setenv("TARJIM_VIDEO_MARK", "yes")
    assert mark.mark_for(Canvas(1920, 1080)) == mark.place_mark(Canvas(1920, 1080))


def burn_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                 placed: mark.Mark | None) -> tuple[list[str], str]:
    seen: list[tuple[list[str], str]] = []

    def fake_run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd is not None
        seen.append((argv, (cwd / burn.PLAIN).read_text(encoding="utf-8")))
        Path(argv[-1]).write_bytes(b"video")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(burn, "run", fake_run)
    monkeypatch.setattr(burn, "video_kbps", lambda _video: 0)
    monkeypatch.setattr(burn, "tool", lambda name: name)
    burn.burn(tmp_path / "v.mp4", render_ass(CUES, Canvas(1280, 720)), tmp_path / "out.mp4",
              placed)
    return seen[0]


def test_the_burn_overlays_the_logo_only_when_the_mark_is_on(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    placed = mark.place_mark(Canvas(1280, 720))
    argv, ass = burn_command(tmp_path, monkeypatch, placed)
    assert argv.count("-i") == 2 and str(mark.LOGO) in argv and "Style: Mark," in ass
    logo = argv.index(str(mark.LOGO))
    assert argv[logo - 5:logo - 1] == media.OWN_PICTURE
    graph = argv[argv.index("-filter_complex") + 1]
    assert f"ass={burn.PLAIN}" in graph and f"overlay={placed.x}:{placed.y}" in graph
    assert f"scale={placed.logo}:{placed.logo}" in graph and "-vf" not in argv
    plain, ass = burn_command(tmp_path, monkeypatch, None)
    assert plain.count("-i") == 1 and "-filter_complex" not in plain and "Mark" not in ass
    assert plain[plain.index("-vf") + 1] == f"ass={burn.PLAIN}"


def test_the_logo_ships_inside_the_package() -> None:
    assert mark.LOGO.is_file() and mark.LOGO.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, job: Job) -> list[tuple[Any, ...]]:
    burned: list[tuple[Any, ...]] = []

    def fake_burn(video: Path, ass: str, target: Path, placed: Any = None) -> Path:
        burned.append((video, ass, target, placed))
        return target

    monkeypatch.setattr(pipeline.media, "probe", lambda _v: media.VideoInfo(1280, 720, 9.0))
    monkeypatch.setattr(pipeline.media, "bright_bottom", lambda _v: False)
    monkeypatch.setattr(pipeline, "placed", lambda _j, _c, canvas, _d: canvas)
    monkeypatch.setattr(pipeline, "burn", fake_burn)
    pipeline.write_outputs(job, CUES, [], pipeline.quiet)
    return burned


def test_subtitle_files_carry_no_mark_while_the_burned_video_does(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = Job(tmp_path / "v.mp4", out_dir=tmp_path, cache_dir=tmp_path / "cache")
    burned = outputs(tmp_path, monkeypatch, job)
    for suffix in (".srt", ".ass"):
        text = job.output(suffix).read_text(encoding="utf-8-sig")
        assert "Cut_Code" not in text and "Mark" not in text
    assert len(burned) == 1 and burned[0][3] == mark.place_mark(Canvas(1280, 720))
    monkeypatch.setenv("TARJIM_VIDEO_MARK", "no")
    assert outputs(tmp_path, monkeypatch, job)[0][3] is None


def test_a_dub_without_burned_subtitles_still_carries_the_mark(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.dub import make

    pictures: list[Path] = []
    monkeypatch.setattr(make, "dub_video", lambda _j, _c, _w, picture: pictures.append(picture))
    job = Job(tmp_path / "v.mp4", burn=False, dub="gemini", out_dir=tmp_path,
              cache_dir=tmp_path / "cache")
    burned = outputs(tmp_path, monkeypatch, job)
    assert len(burned) == 1 and burned[0][3] is not None and "Dialogue: 0" not in burned[0][1]
    assert pictures == [burned[0][2]] and burned[0][2].parent == job.cache
    monkeypatch.setenv("TARJIM_VIDEO_MARK", "no")
    assert outputs(tmp_path, monkeypatch, job) == [] and pictures[-1] == job.video
