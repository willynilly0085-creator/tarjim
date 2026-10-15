"""A cancelled job leaves nothing it made behind: not the pieces of a download ffmpeg was fetching,
not its results, not its work folder. What was there before the job stays, and so does a source
that was fully downloaded, so Retry can use it."""
import http.server
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar

import psutil
import pytest

import tarjim.pipeline
from tarjim import fetch
from tarjim.job import Job
from tarjim.server import __main__ as engine
from tarjim.server.jobs import Board, Order

SOON = 2.0
FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")


def until(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return check()


def names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


def ffmpegs() -> list[Any]:
    return [p for p in psutil.Process().children(recursive=True)
            if "ffmpeg" in p.name().lower()]


def gone(process: Any) -> bool:
    try:
        return bool(process.status() == psutil.STATUS_ZOMBIE)
    except psutil.NoSuchProcess:
        return True


def encrypted_stream(folder: Path) -> dict[str, bytes]:
    """Thirty one-second pieces under AES-128. Without pycryptodomex the downloader hands such a
    stream to ffmpeg, which reports nothing while it runs."""
    subprocess.run([str(FFMPEG), "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=s=96x64:r=10",
                    "-f", "lavfi", "-i", "sine", "-t", "30", "-g", "10", "-c:v", "libx264",
                    "-c:a", "aac", "-f", "hls", "-hls_time", "1", "-hls_list_size", "0",
                    "-hls_enc", "1", "-hls_enc_key", "00112233445566778899aabbccddeeff",
                    "-hls_enc_key_url", "key.bin", "-hls_segment_filename", "seg%d.ts",
                    "v.m3u8"], check=True, cwd=folder)
    return {f"/{p.name}": p.read_bytes() for p in folder.iterdir()}


class Slow(http.server.BaseHTTPRequestHandler):
    files: ClassVar[dict[str, bytes]] = {}
    delay: ClassVar[float] = 0.3

    def do_GET(self) -> None:
        body = self.files.get(self.path.split("?")[0], b"")
        if self.path.endswith(".ts"):
            time.sleep(self.delay)
        try:
            self.send_response(200 if body else 404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            return

    def log_message(self, *_args: Any) -> None:
        return None


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(engine, "HOME", tmp_path / "home")
    monkeypatch.setattr(fetch, "tool", lambda name: shutil.which(name) or name)
    return tmp_path / "home"


@pytest.fixture
def site(tmp_path: Path) -> Iterator[str]:
    (tmp_path / "stream").mkdir()
    Slow.files = encrypted_stream(tmp_path / "stream")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v.m3u8"
    server.shutdown()


@needs_ffmpeg
def test_a_cancel_stops_ffmpeg_fetching_a_stream_and_leaves_no_piece(
        home: Path, site: str, tmp_path: Path) -> None:
    Slow.delay = 0.3
    board = Board(lambda task: engine.perform(task, tmp_path / "out"))
    task = board.submit(Order(site, mode="srt"))
    sources = home / "sources"
    assert until(lambda: bool(ffmpegs()) and any(sources.glob("*.part")), 20)
    fetching = ffmpegs()
    board.steer(task.id, "cancel", "test")
    assert until(lambda: task.stage == "cancelled", SOON)
    assert until(lambda: all(gone(p) for p in fetching), SOON)
    assert until(lambda: names(sources) == [], SOON)


@needs_ffmpeg
def test_a_source_fully_downloaded_stays_for_retry(
        home: Path, site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    Slow.delay = 0.0
    working, gate = threading.Event(), threading.Event()

    def run(job: Job, report: Any) -> None:
        report("hearing")
        working.set()
        gate.wait(30)

    monkeypatch.setattr(tarjim.pipeline, "run", run)
    board = Board(lambda task: engine.perform(task, tmp_path / "out"))
    task = board.submit(Order(site, mode="srt"))
    assert working.wait(60)
    board.steer(task.id, "cancel", "test")
    assert until(lambda: task.stage == "cancelled", SOON)
    assert task.video is not None and names(home / "sources") == [task.video.name]
    gate.set()


class Halfway:
    """A run that wrote work and half its results, is then stuck where a cancel cannot reach,
    and writes once more after it."""

    def __init__(self) -> None:
        self.halfway, self.gate, self.late = threading.Event(), threading.Event(), threading.Event()

    def __call__(self, job: Job, report: Any) -> None:
        job.claim_cache()
        (job.cache / "transcript.json").write_text("{}", encoding="utf-8")
        report("burning")
        job.output(".ass").write_text("cues", encoding="utf-8")
        job.output(".mp4").write_bytes(b"half a video")
        self.halfway.set()
        self.gate.wait(30)
        job.output(".dub.mp4").write_bytes(b"written after the cancel")
        self.late.set()


@pytest.fixture
def private(home: Path, tmp_path: Path) -> Path:
    """The person's own video, an earlier result and a file of theirs, another video's work."""
    (tmp_path / "private").mkdir()
    (tmp_path / "out").mkdir()
    (tmp_path / "private" / "talk.mp4").write_bytes(b"the person's video")
    (tmp_path / "out" / "talk.ar.srt").write_text("an earlier result", encoding="utf-8")
    (tmp_path / "out" / "notes.txt").write_text("the person's own file", encoding="utf-8")
    (home / "cache" / "other").mkdir(parents=True)
    return tmp_path / "private"


def test_a_cancelled_job_takes_back_its_results_and_its_work_and_nothing_else(
        home: Path, private: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run, out = Halfway(), private.parent / "out"
    monkeypatch.setattr(tarjim.pipeline, "run", run)
    board = Board(lambda task: engine.perform(task, out))
    task = board.submit(Order(str(private / "talk.mp4")))
    assert run.halfway.wait(5)
    board.steer(task.id, "cancel", "test")
    assert until(lambda: task.stage == "cancelled", SOON)
    assert names(out) == ["notes.txt", "talk.ar.srt"] and names(home / "cache") == ["other"]
    run.gate.set()
    assert run.late.wait(5)
    assert until(lambda: names(out) == ["notes.txt", "talk.ar.srt"])
    assert (private / "talk.mp4").read_bytes() == b"the person's video"
    assert (out / "talk.ar.srt").read_text(encoding="utf-8") == "an earlier result"
    assert task.stage == "cancelled" and task.outputs == []
