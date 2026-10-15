"""One link downloads at most 8 GB in all. A video and its sound are two downloads, and some
streams are handed to ffmpeg, which reports nothing while it runs; neither gets past the limit."""
import http.server
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tarjim import fetch

youtube = pytest.importorskip("yt_dlp.extractor.youtube")
FFMPEG = shutil.which("ffmpeg")
PIECE = 20_000
FILES: dict[str, bytes] = {"/v.mp4": bytes(PIECE), "/a.m4a": bytes(PIECE)}


def stream() -> bytes:
    """A stream of sixty pieces marked with an encryption the native downloader leaves to
    ffmpeg (the mark sits in each piece's title, which ffmpeg does not read)."""
    head = ["#EXTM3U", "#EXT-X-TARGETDURATION:1"]
    pieces = [f"#EXTINF:1.0,#EXT-X-KEY:METHOD=SAMPLE-AES\nseg.ts?n={k}" for k in range(60)]
    return "\n".join([*head, *pieces, "#EXT-X-ENDLIST", ""]).encode()


class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        body = stream() if path == "/v.m3u8" else FILES[path]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return None


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setattr(fetch, "tool", lambda name: shutil.which(name) or name)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def written(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.rglob("*")) if folder.exists() else []


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg to merge the two pieces")
def test_a_video_and_its_sound_share_one_limit(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def video(ie: Any, url: str) -> dict[str, Any]:
        return {"id": ie._match_id(url), "title": "talk", "formats": [
            {"format_id": "v", "url": f"{site}/v.mp4", "ext": "mp4", "vcodec": "avc1",
             "acodec": "none", "height": 480},
            {"format_id": "a", "url": f"{site}/a.m4a", "ext": "m4a", "vcodec": "none",
             "acodec": "mp4a"}]}

    monkeypatch.setattr(youtube.YoutubeIE, "_real_extract", video)
    monkeypatch.setattr(fetch, "LARGEST", PIECE * 3 // 2)
    with pytest.raises(RuntimeError, match="8 GB"):
        fetch.download("https://www.youtube.com/watch?v=abcdefghijk", tmp_path)
    assert written(tmp_path) == []


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")
def test_a_stream_handed_to_ffmpeg_stops_at_the_limit(
        site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clip = tmp_path / "clip.ts"
    subprocess.run([str(FFMPEG), "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=160x120",
                    "-f", "lavfi", "-i", "sine", "-t", "1", "-c:v", "libx264", "-c:a", "aac",
                    "-f", "mpegts", str(clip)], check=True)
    FILES["/seg.ts"] = clip.read_bytes()
    clip.unlink()
    monkeypatch.setattr(fetch, "LARGEST", 10 * len(FILES["/seg.ts"]))
    with pytest.raises(RuntimeError, match="8 GB"):
        fetch.download(f"{site}/v.m3u8", tmp_path / "out")
    assert written(tmp_path / "out") == []
