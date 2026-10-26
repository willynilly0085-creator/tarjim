"""An order that cannot be made is refused when it is sent, not at the end of the work; the job
buttons say why they could not act; and the list of recent jobs outlives a reboot."""
import http.client
import json
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from tarjim import config
from tarjim.server import job_record
from tarjim.server.app import Handler
from tarjim.server.jobs import Board, Order, Task

TOKEN = "refusal-token"


@pytest.fixture
def board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Board:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    return Board(lambda task: None)


@pytest.fixture
def port(board: Board, tmp_path: Path) -> Iterator[int]:
    Handler.board, Handler.token, Handler.uploads = board, TOKEN, tmp_path / "uploads"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def call(port: int, request: str, data: object = None) -> tuple[int, dict[str, object]]:
    method, path = request.split(" ", 1)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    body = json.dumps(data).encode() if data is not None else b""
    conn.request(method, path, body=body, headers={"X-Tarjim-Token": TOKEN,
                                                   "Content-Type": "application/json"})
    response = conn.getresponse()
    return response.status, json.loads(response.read() or b"{}")


def test_a_dub_into_a_language_no_voice_speaks_is_refused_when_sent(port: int) -> None:
    order = {"url": "https://example.com/v", "target": "am", "mode": "dub-clone"}
    assert call(port, "POST /jobs", order) == (400, {"error": "dub_language"})
    assert call(port, "POST /jobs/check", order) == (400, {"error": "dub_language"})
    assert call(port, "POST /jobs/check", {**order, "mode": "srt"}) == (200, {"ok": True})
    assert call(port, "POST /jobs/check", {**order, "mode": "evil"})[1] == {"error": "mode"}


def test_a_linked_voice_without_its_key_is_refused_when_sent(port: int) -> None:
    order = {"url": "https://example.com/v", "target": "fr", "mode": "dub-eleven"}
    assert call(port, "POST /jobs", order) == (400, {"error": "dub_key"})


def test_a_file_that_was_moved_says_so_instead_of_failing_silently(
        board: Board, port: int, tmp_path: Path) -> None:
    task = Task(Order("https://example.com/v"))
    task.outputs, task.stage = [tmp_path / "gone.ar.mp4"], "done"
    board.tasks[task.id] = task
    assert call(port, f"POST /open/{task.id}") == (404, {"error": "gone"})
    assert call(port, f"POST /reveal/{task.id}") == (404, {"error": "gone"})


def test_the_recent_jobs_outlive_a_reboot_and_a_removal_is_kept(
        board: Board, tmp_path: Path) -> None:
    job_record.keep(board, tmp_path)
    task = board.submit(Order("https://example.com/v", target="fr", mode="srt"))
    for _ in range(100):
        if task.finished and (tmp_path / job_record.JOBS).exists():
            break
        threading.Event().wait(0.02)
    after_reboot = Board(lambda task: None)
    job_record.keep(after_reboot, tmp_path)
    assert after_reboot.get(task.id) is not None
    assert after_reboot.remove(task.id)
    again = Board(lambda task: None)
    job_record.keep(again, tmp_path)
    assert again.get(task.id) is None
