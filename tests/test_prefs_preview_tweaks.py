"""One real frame drawn with values not saved yet, and an order's own settings refused before
its job starts (2026-11-09)."""
import base64
import http.client
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from prefs_server import TOKEN, ask, serving

from tarjim.prefs.model import Prefs
from tarjim.render import font_cover, preview
from tarjim.render.preview import Shot, Still
from tarjim.server.jobs import Board

FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch) -> Board:
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    monkeypatch.setattr(font_cover, "covering", lambda _code: ["Dubai", "Arial"])
    return Board(lambda _task: None)


@pytest.fixture
def port(prefs_home: Path, tmp_path: Path, board: Board) -> Iterator[int]:
    with serving(board, tmp_path / "uploads") as found:
        yield found


@pytest.fixture
def drawn(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Prefs, Shot]]:
    seen: list[tuple[Prefs, Shot]] = []

    def still(prefs: Prefs, shot: Shot) -> Still:
        seen.append((prefs, shot))
        return Still(b"\xff\xd8jpeg", 1920, 1080, "Dubai-Bold", False)

    monkeypatch.setattr(preview, "still", still)
    return seen


def test_the_preview_draws_values_not_saved_and_refuses_the_rest(
        port: int, drawn: list[tuple[Prefs, Shot]]) -> None:
    code, out = ask(port, "POST /prefs/preview", {
        "values": {"look.size_wide": 115, "look.box_opacity": 10}, "portrait": True})
    assert code == 200 and out["image"] == "data:image/jpeg;base64," + base64.b64encode(
        b"\xff\xd8jpeg").decode()
    assert out["font"] == "Dubai-Bold" and list(out["refused"]) == ["look.box_opacity"]
    prefs, shot = drawn[0]
    assert prefs.look.size_wide == 115 and prefs.look.box_opacity == 69
    assert shot == Shot(None, 0.0, True, "")
    assert ask(port, "GET /prefs")[1]["changed"] == []  # nothing was saved


def test_the_preview_takes_the_persons_own_video_or_says_it_cannot(
        port: int, drawn: list[tuple[Prefs, Shot]], tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"video")
    assert ask(port, "POST /prefs/preview", {"path": str(clip), "at": "12.5"})[0] == 200
    assert drawn[0][1].video == clip.resolve() and drawn[0][1].at == 12.5
    for wrong in ({"path": str(tmp_path / "gone.mp4")}, {"path": "clip.mp4"},
                  {"job": "0123456789ab"}, {"values": []}, {"language": "xx"}):
        assert ask(port, "POST /prefs/preview", wrong) == (400, {"error": "preview"})


def test_a_preview_without_ffmpeg_says_so(port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_prefs: Prefs, _shot: Shot) -> Still:
        raise FileNotFoundError("ffmpeg not found")

    monkeypatch.setattr(preview, "still", missing)
    assert ask(port, "POST /prefs/preview", {}) == (503, {"error": "ffmpeg", "refused": {}})


@needs_ffmpeg
def test_the_preview_is_a_real_frame_drawn_by_libass(port: int, tmp_path: Path) -> None:
    code, out = ask(port, "POST /prefs/preview", {"values": {"look.style": "outline"},
                                                  "portrait": True})
    image = base64.b64decode(out["image"].split(",", 1)[1])
    assert code == 200 and image[:2] == b"\xff\xd8" and (out["width"], out["height"]) == (
        1080, 1920)
    clip = tmp_path / "clip.mp4"
    subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=s=320x240:d=2", str(clip)], check=True, timeout=60)
    code, out = ask(port, "POST /prefs/preview", {"path": str(clip), "at": 1, "text": "hi"})
    assert code == 200 and (out["width"], out["height"]) == (320, 240)


def test_the_sample_line_is_two_speakers_the_first_one_main() -> None:
    cue = preview.sample_cue(preview.spoken("", "ar"))
    assert cue.is_dialogue and [p[0].speaker for p in cue.parts] == ["A", "B"]
    assert preview.spoken("  one ||  two || three ", "en") == ["one", "two"]
    assert preview.spoken("", "ja") == list(preview.SAMPLES["en"])
    assert preview.picked("fontselect: (Dubai, 700, 0) -> Dubai-Bold, 0, Dubai-Bold\n"
                          "fontselect: (Segoe UI, 400, 0) -> SegoeUI, 0, SegoeUI", "dubai") == (
        "Dubai-Bold")


def order(**more: Any) -> dict[str, Any]:
    return {"url": "https://example.com/v", "target": "ar", **more}


def test_an_orders_own_settings_are_refused_before_its_job_starts(port: int) -> None:
    tweaks = {"look.size_wide": 300, "output.folder": "C:\\", "look.font": "Comic Sans MS",
              "look.nope": 1}
    code, out = ask(port, "POST /jobs", order(tweaks=tweaks))
    assert code == 400 and out["error"] == "tweaks" and set(out["refused"]) == set(tweaks)
    assert "ما يتغير لفيديو واحد" in out["refused"]["output.folder"]
    assert "Arial" in out["refused"]["look.font"]
    assert ask(port, "POST /jobs/check", order(tweaks={"look.size_wide": 300}))[1][
        "refused"]["look.size_wide"].startswith("«حجم الخط")


def test_an_orders_own_settings_go_with_it_and_are_not_saved(port: int, board: Board) -> None:
    code, job = ask(port, "POST /jobs", order(tweaks={"look.size_wide": 110}))
    task = board.get(job["id"])
    assert code == 200 and task is not None
    assert task.order.prefs["values"] == {"look.size_wide": 110}
    assert ask(port, "GET /prefs")[1]["changed"] == []


def test_an_uploads_own_settings_ride_in_its_address(port: int) -> None:
    def upload(tweaks: str) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", f"/upload?name=a.mp4&target=ar&tweaks={tweaks}", body=b"v",
                     headers={"X-Tarjim-Token": TOKEN})
        response = conn.getresponse()
        return response.status, response.read()

    assert upload("not-json")[0] == 400 and b'"tweaks"' in upload("not-json")[1]
    status, body = upload("%7B%22look.size_wide%22%3A300%7D")
    assert status == 400 and b"look.size_wide" in body
    assert upload("%7B%22look.size_wide%22%3A110%7D")[0] == 200
