"""An ended job can be removed from the list, on the page, in the extension and in chat. Only the
list changes: the files it made stay, a running job is never removed, and a restart forgets it."""
import http.client
import json
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from tarjim.server import renew
from tarjim.server.app import Handler
from tarjim.server.jobs import Board, Order, Task
from tarjim.ui_languages import FOLDER, codes

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
TOKEN = "remove-token"


def call(port: int, request: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    method, path = request.split(" ", 1)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=b"", headers={"X-Tarjim-Token": TOKEN, **(headers or {})})
    response = conn.getresponse()
    return response.status, response.read()


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch) -> Board:
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    return Board(lambda task: None)


def ended(board: Board, stage: str, output: Path | None = None) -> Task:
    task = Task(Order(f"https://example.com/{stage}"))
    task.outputs = [output] if output else []
    task.stage = stage
    board.tasks[task.id] = task
    return task


@pytest.fixture
def port(board: Board, tmp_path: Path) -> Iterator[int]:
    Handler.board, Handler.token, Handler.uploads = board, TOKEN, tmp_path / "uploads"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


@pytest.mark.parametrize("stage", ["done", "failed", "cancelled"])
def test_an_ended_job_leaves_the_list_and_its_files_stay(
        board: Board, port: int, tmp_path: Path, stage: str) -> None:
    video = tmp_path / "clip.ar.mp4"
    video.write_bytes(b"video")
    task = ended(board, stage, video)
    code, body = call(port, f"POST /jobs/{task.id}/remove")
    assert code == 200 and json.loads(body) == {"removed": True}
    assert board.get(task.id) is None and video.read_bytes() == b"video"
    listed = json.loads(call(port, "GET /jobs")[1])
    assert all(job["id"] != task.id for job in listed)


@pytest.mark.parametrize("stage", ["queued", "hearing", "translating"])
def test_a_queued_or_running_job_is_never_removed(board: Board, port: int, stage: str) -> None:
    task = ended(board, stage)
    assert call(port, f"POST /jobs/{task.id}/remove")[0] == 409
    assert board.get(task.id) is task
    assert not board.remove("000000000000")


def test_removing_needs_the_token(board: Board, port: int) -> None:
    task = ended(board, "done")
    assert call(port, f"POST /jobs/{task.id}/remove", headers={"X-Tarjim-Token": ""})[0] == 403
    assert call(port, f"POST /jobs/{task.id}/remove", headers={"X-Tarjim-Token": "x"})[0] == 403
    assert board.get(task.id) is task


def test_a_removed_job_does_not_come_back_after_a_restart(board: Board, tmp_path: Path) -> None:
    kept, gone = ended(board, "failed"), ended(board, "done")
    assert board.remove(gone.id)
    renew.write_down(board, tmp_path)
    rows: list[dict[str, Any]] = json.loads((tmp_path / renew.JOBS).read_text(encoding="utf-8"))
    assert [row["id"] for row in rows] == [kept.id]
    again = Board(lambda task: None)
    renew.restore(again, tmp_path)
    assert again.get(kept.id) is not None and again.get(gone.id) is None


def test_chat_can_remove_an_ended_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import assistant

    asked: list[str] = []
    monkeypatch.setattr(assistant, "call", lambda path, body=None: asked.append(path) or {})
    assistant.control_translation("abc123abc123", "remove")
    assert asked == ["/jobs/abc123abc123/remove"]


def test_the_remove_button_and_the_translator_switch_speak_every_language() -> None:
    page_keys = ("remove", "removeLabel", "removeSure", "removed", "engineWith", "engineChange",
                 "engineNone", "engineSaving")
    for code in codes():
        page = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        extension = json.loads((ROOT / "extension" / "_locales" / code / "messages.json")
                               .read_text(encoding="utf-8"))
        assert all(page.get(key) for key in page_keys), code
        assert all(extension[key]["message"] == page[key] for key in page_keys), code
    for path in ("web/jobs.js", "extension/jobs.js"):
        assert "/remove`" in (ROOT / path).read_text(encoding="utf-8"), path
    for path in ("web/engine.js", "extension/engine.js"):
        assert '"/connections/use"' in (ROOT / path).read_text(encoding="utf-8"), path


def test_a_queued_job_shows_cancelled_at_once_and_can_then_be_removed(board: Board) -> None:
    task = Task(Order("https://example.com/waiting"))
    board.tasks[task.id] = task
    assert board.steer(task.id, "cancel") is task
    assert task.stage == "cancelled" and task.finished
    task.stage = "downloading"  # a worker reaching it later changes nothing
    assert task.stage == "cancelled" and board.remove(task.id)
