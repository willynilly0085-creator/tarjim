"""A link's qualities are read before anything downloads, offered with their sizes, and exactly
the one picked is downloaded with its sound. Real yt-dlp against a site on this computer; the
YouTube extractor is told what formats the video has."""
import http.server
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest

from tarjim import fetch
from tarjim.server.jobs import Order
from tarjim.server.orders import order_from
from tarjim.server.quality_routes import QualityRoutes

youtube = pytest.importorskip("yt_dlp.extractor.youtube")
FFMPEG = shutil.which("ffmpeg")
URL = "https://www.youtube.com/watch?v=abcdefghijk"
SECONDS = 100


def made(folder: Path, name: str, source: list[str]) -> bytes:
    """A one-second clip, real enough for ffmpeg to merge."""
    target = folder / name
    subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", *source, "-t", "1", str(target)],
                   check=True)
    return target.read_bytes()


@pytest.fixture(scope="module")
def clips(tmp_path_factory: pytest.TempPathFactory) -> dict[str, bytes]:
    if not FFMPEG:
        pytest.skip("needs ffmpeg to make and merge the clips")
    folder = tmp_path_factory.mktemp("clips")
    return {"video": made(folder, "v.mp4", ["-f", "lavfi", "-i", "testsrc=size=64x36:rate=10",
                                            "-c:v", "mpeg4"]),
            "sound": made(folder, "a.m4a", ["-f", "lavfi", "-i", "sine", "-c:a", "aac"])}


class Site(http.server.BaseHTTPRequestHandler):
    clips: ClassVar[dict[str, bytes]] = {}
    asked: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        self.asked.append(path)
        body = self.clips["sound" if path.startswith("/a") else "video"]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return None


def formats(site: str, portrait: bool = False) -> list[dict[str, Any]]:
    def picture(name: str, height: int, codec: str, **more: Any) -> dict[str, Any]:
        sides = (height, height * 16 // 9)
        width, tall = sides if portrait else sides[::-1]
        return {"format_id": name, "url": f"{site}/{name}.mp4", "ext": "mp4", "vcodec": codec,
                "acodec": "none", "width": width, "height": tall, "tbr": height, **more}

    return [{"format_id": "18", "url": f"{site}/v18.mp4", "ext": "mp4", "vcodec": "avc1",
             "acodec": "mp4a", "width": 640, "height": 360, "tbr": 500},
            {"format_id": "a140", "url": f"{site}/a140.m4a", "ext": "m4a", "vcodec": "none",
             "acodec": "mp4a", "tbr": 128, "filesize": 1_600_000},
            {"format_id": "a251", "url": f"{site}/a251.webm", "ext": "webm", "vcodec": "none",
             "acodec": "opus", "tbr": 140},
            picture("v720", 720, "avc1"), picture("v1080", 1080, "avc1", filesize=50_000_000),
            picture("v2160hdr", 2160, "vp9.2", dynamic_range="HDR10", tbr=30000),
            picture("v2160", 2160, "vp9", dynamic_range="SDR", tbr=20000)]


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch, clips: dict[str, bytes]) -> Iterator[str]:
    monkeypatch.setattr(fetch, "tool", lambda name: shutil.which(name) or name)
    Site.clips, Site.asked = clips, []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def video_has(monkeypatch: pytest.MonkeyPatch, found: list[dict[str, Any]]) -> None:
    def video(ie: Any, url: str) -> dict[str, Any]:
        return {"id": ie._match_id(url), "title": "talk", "duration": SECONDS, "formats": found}

    monkeypatch.setattr(youtube.YoutubeIE, "_real_extract", video)


def test_every_quality_is_offered_with_its_size_and_1080p_first_choice(
        site: str, monkeypatch: pytest.MonkeyPatch) -> None:
    video_has(monkeypatch, formats(site))
    found = fetch.look(URL)
    assert [c["label"] for c in found["choices"]] == ["2160p", "1080p", "720p", "360p"]
    sizes = {c["id"]: c["size"] for c in found["choices"]}
    assert sizes["1080"] == 50_000_000 + 1_600_000  # the picture and the sound it is merged with
    assert sizes["2160"] == 20000 * 125 * SECONDS + 1_600_000  # SDR, estimated from its rate
    assert found["default"] == "1080" and found["audio"] == {"size": 1_600_000}
    assert found["limit"] == fetch.LARGEST and Site.asked == []  # nothing was downloaded


@pytest.mark.parametrize("case", [
    ("", ["/v1080.mp4", "/a140.m4a"], " 1080p.mp4"),
    ("720", ["/v720.mp4", "/a140.m4a"], " 720p.mp4"),
    ("2160", ["/v2160.mp4", "/a140.m4a"], " 2160p.mp4"),
    ("1440", ["/v1080.mp4", "/a140.m4a"], " 1080p.mp4"),
    ("audio", ["/a140.m4a"], " audio.m4a"),
])
def test_exactly_the_picked_quality_is_downloaded_with_its_sound(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        case: tuple[str, list[str], str]) -> None:
    quality, pieces, suffix = case
    video_has(monkeypatch, formats(site))
    video = fetch.download(URL, tmp_path, quality)
    assert sorted(Site.asked) == sorted(pieces)
    assert video.name.endswith(suffix) and [p.name for p in tmp_path.iterdir()] == [video.name]


def test_a_portrait_video_is_named_by_its_shorter_side(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_has(monkeypatch, formats(site, portrait=True))
    assert [c["label"] for c in fetch.look(URL)["choices"]] == ["2160p", "1080p", "720p", "360p"]
    video = fetch.download(URL, tmp_path, "720")
    assert "/v720.mp4" in Site.asked and video.name.endswith(" 720p.mp4")


def test_a_link_with_one_unnamed_quality_offers_no_choice_and_still_downloads(
        site: str, tmp_path: Path) -> None:
    found = fetch.look(f"{site}/plain.mp4")
    assert found["choices"] == [] and found["default"] == "" and found["audio"] is None
    assert fetch.download(f"{site}/plain.mp4", tmp_path, "720").read_bytes() == Site.clips["video"]


class Asked(QualityRoutes):
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body
        self.replies: list[tuple[int, Any]] = []

    def read_json(self) -> dict[str, Any]:
        return self.body

    def reply(self, code: int, payload: Any) -> None:
        self.replies.append((code, payload))


def test_the_page_asks_the_engine_for_a_links_qualities(
        site: str, monkeypatch: pytest.MonkeyPatch) -> None:
    video_has(monkeypatch, formats(site))
    asked = Asked({"url": URL})
    asked.link_qualities({})
    (code, found), = asked.replies
    assert code == 200 and found["default"] == "1080" and len(found["choices"]) == 4


@pytest.mark.parametrize(("body", "code", "error"), [
    ({"url": "file:///etc/passwd"}, 400, "bad url"),
    ({"url": "https://www.youtube.com/playlist?list=PLx"}, 422, "list"),
    ({"url": "http://127.0.0.1:9/nothing.mp4"}, 422, "download"),
])
def test_a_link_without_qualities_says_why(
        monkeypatch: pytest.MonkeyPatch, body: dict[str, str], code: int, error: str) -> None:
    def playlist(ie: Any, url: str, smuggled: Any = None) -> dict[str, Any]:
        entries = [ie.url_result(f"https://www.youtube.com/watch?v={k * 11}") for k in "ab"]
        return ie.playlist_result(entries, "PLx", "a list")

    monkeypatch.setattr(youtube.YoutubeTabIE, "_real_extract", playlist)
    asked = Asked(body)
    asked.link_qualities({})
    assert asked.replies == [(code, {"error": error})]


@pytest.mark.parametrize(("data", "quality"), [
    ({"quality": "720"}, "720"), ({"quality": "AUDIO", "mode": "srt"}, "audio"),
    ({"quality": "audio", "mode": "burn"}, ""), ({"quality": "audio", "mode": "dub-gemini"}, ""),
    ({"quality": "720; calc"}, ""), ({"quality": 1080}, "1080"), ({}, ""),
    ({"quality": "9" * 9}, ""),
])
def test_an_order_carries_only_a_quality_it_can_use(data: dict[str, Any], quality: str) -> None:
    assert order_from(URL, data).quality == quality


def test_a_job_saved_before_qualities_existed_still_loads() -> None:
    assert Order(**{"source": URL, "target": "ar", "mode": "burn", "dialect": "saudi",
                    "name": ""}).quality == ""


def test_the_engine_downloads_the_quality_the_order_carries(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.server import engine
    from tarjim.server.jobs import Task

    asked: list[tuple[str, str]] = []

    def resolve(source: str, _folder: Path, quality: str = "") -> Path:
        asked.append((source, quality))
        raise RuntimeError("stop here")

    monkeypatch.setattr(engine, "resolve", resolve)
    task = Task(order_from(URL, {"quality": "720", "mode": "burn"}))
    with pytest.raises(RuntimeError, match="stop here"):
        engine.perform(task, tmp_path)
    assert asked == [(URL, "720")] and task.stage == "downloading"
