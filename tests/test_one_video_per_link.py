"""A link gives one video. A link that is a list of videos (a feed, a playlist, a channel, a page
with several videos) is refused before anything is written, and a download that fails or is
cancelled leaves nothing behind in the folder."""
import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import fetch
from tarjim.job import CHECKPOINT
from tarjim.server.jobs import Stopped, classify
from tarjim.ui_languages import FOLDER, codes

youtube = pytest.importorskip("yt_dlp.extractor.youtube")
ROOT = Path(__file__).resolve().parents[1] / "tarjim"
CLIP = b"\x00\x00\x00\x18ftypmp42" + bytes(40_000)
TYPES = {".xml": "application/rss+xml", ".html": "text/html", ".mp4": "video/mp4"}


def feed(site: str) -> str:
    items = "".join(f'<item><title>Episode {k}</title><enclosure url="{site}/clip{k}.mp4" '
                    f'type="video/mp4" length="{len(CLIP)}"/></item>' for k in range(3))
    return (f'<?xml version="1.0"?><rss version="2.0"><channel><title>a feed</title>{items}'
            "</channel></rss>")


def page(site: str) -> str:
    videos = "".join(f'<video src="{site}/clip{k}.mp4"></video>' for k in range(3))
    return f"<html><head><title>lectures</title></head><body>{videos}</body></html>"


class Site(http.server.BaseHTTPRequestHandler):
    """Serves a feed, a page with three videos, and clips; stream.mp4 comes without a length."""

    def do_GET(self) -> None:
        path, site = self.path.split("?")[0], f"http://{self.headers['Host']}"
        body = {"/feed.xml": feed(site), "/page.html": page(site)}.get(path, "").encode() or CLIP
        self.send_response(200)
        self.send_header("Content-Type", TYPES[Path(path).suffix or ".html"])
        if path != "/stream.mp4":
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return None


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setattr(fetch, "tool", lambda name: name)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def written(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.rglob("*")) if folder.exists() else []


@pytest.mark.parametrize("name", ["feed.xml", "page.html"])
def test_a_link_to_a_list_is_refused_before_anything_is_written(
        site: str, tmp_path: Path, name: str) -> None:
    with pytest.raises(RuntimeError) as refused:
        fetch.download(f"{site}/{name}", tmp_path)
    assert classify(refused.value) == "list" and written(tmp_path) == []


def test_a_link_to_one_video_still_downloads_it(site: str, tmp_path: Path) -> None:
    video = fetch.download(f"{site}/one.mp4", tmp_path)
    assert video.read_bytes() == CLIP and written(tmp_path) == [video.name]


def test_a_download_stopped_at_the_size_limit_leaves_nothing(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "LARGEST", 1000)
    with pytest.raises(RuntimeError, match="8 GB"):
        fetch.download(f"{site}/stream.mp4", tmp_path)
    assert written(tmp_path) == []


def test_a_cancelled_download_leaves_nothing_and_keeps_what_was_there(
        site: str, tmp_path: Path) -> None:
    (tmp_path / "earlier [e].mp4").write_bytes(CLIP)

    def cancel() -> None:
        raise Stopped

    token = CHECKPOINT.set(cancel)
    try:
        with pytest.raises(Stopped):
            fetch.download(f"{site}/one.mp4", tmp_path)
    finally:
        CHECKPOINT.reset(token)
    assert written(tmp_path) == ["earlier [e].mp4"]


def fake_youtube(monkeypatch: pytest.MonkeyPatch, site: str) -> list[str]:
    """YouTube without the network: a video id resolves to a clip on this computer."""
    asked: list[str] = []

    def video(ie: Any, url: str) -> dict[str, Any]:
        asked.append(url)
        return {"id": ie._match_id(url), "title": "one talk", "url": f"{site}/talk.mp4",
                "ext": "mp4"}

    monkeypatch.setattr(youtube.YoutubeIE, "_real_extract", video)
    return asked


def test_a_video_link_that_also_names_its_playlist_takes_just_the_video(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = fake_youtube(monkeypatch, site)
    video = fetch.download("https://www.youtube.com/watch?v=abcdefghijk&list=PLx", tmp_path)
    assert asked == ["https://www.youtube.com/watch?v=abcdefghijk"]
    assert written(tmp_path) == [video.name] and "abcdefghijk" in video.name


def test_a_youtube_playlist_is_refused_without_opening_its_videos(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = fake_youtube(monkeypatch, site)

    def playlist(ie: Any, url: str, smuggled: Any = None) -> dict[str, Any]:
        entries = [ie.url_result(f"https://www.youtube.com/watch?v={k * 11}", youtube.YoutubeIE)
                   for k in "abc"]
        return ie.playlist_result(entries, "PLx", "a list")

    monkeypatch.setattr(youtube.YoutubeTabIE, "_real_extract", playlist)
    with pytest.raises(RuntimeError) as refused:
        fetch.download("https://www.youtube.com/playlist?list=PLx", tmp_path)
    assert classify(refused.value) == "list" and asked == [] and written(tmp_path) == []


def test_the_reason_is_shown_in_every_language() -> None:
    for code in codes():
        page = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        extension = json.loads((ROOT / "extension" / "_locales" / code / "messages.json")
                               .read_text(encoding="utf-8"))
        assert page.get("err_list") and extension.get("errList", {}).get("message"), code
    assert '"list"' in (ROOT / "web" / "jobs.js").read_text(encoding="utf-8")
    assert 'list: "errList"' in (ROOT / "extension" / "shared.js").read_text(encoding="utf-8")
