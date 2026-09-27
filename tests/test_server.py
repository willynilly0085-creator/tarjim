import http.client
import json
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from tarjim.server.app import Handler
from tarjim.server.guard import safe_name
from tarjim.server.jobs import Board, Task

TOKEN = "secret-token"


@pytest.fixture
def server(tmp_path: Path):  # type: ignore[no-untyped-def]
    done: list[Task] = []

    def work(task: Task) -> None:
        output = tmp_path / "out.ar.srt"
        output.write_text("1", encoding="utf-8")
        task.outputs = [output]
        done.append(task)

    Handler.board, Handler.token, Handler.uploads = Board(work), TOKEN, tmp_path / "uploads"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1], done
    httpd.shutdown()


def call(port: int, request: str, body: bytes = b"",
         headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    method, path = request.split(" ", 1)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers={"X-Tarjim-Token": TOKEN, **(headers or {})})
    response = conn.getresponse()
    return response.status, response.read()


def test_ping_is_open_but_jobs_need_the_token(server) -> None:  # type: ignore[no-untyped-def]
    port, _ = server
    assert call(port, "GET /ping", headers={"X-Tarjim-Token": ""})[0] == 200
    assert call(port, "GET /jobs", headers={"X-Tarjim-Token": "wrong"})[0] == 403


def test_foreign_host_header_is_refused(server) -> None:  # type: ignore[no-untyped-def]
    port, _ = server
    assert call(port, "GET /jobs", headers={"Host": "evil.example"})[0] == 403


def test_link_job_runs_and_its_output_can_be_downloaded(server) -> None:  # type: ignore[no-untyped-def]
    port, done = server
    body = json.dumps({"url": "https://example.com/v", "target": "fr", "mode": "srt"}).encode()
    status, raw = call(port, "POST /jobs", body=body,
                       headers={"Content-Type": "application/json"})
    job = json.loads(raw)
    assert status == 200 and job["target"] == "fr"
    for _ in range(50):
        if done:
            break
        time.sleep(0.02)
    assert call(port, f"GET /files/{job['id']}/out.ar.srt")[0] == 200
    assert call(port, f"GET /files/{job['id']}/..%2F..%2Fsecret.txt")[0] == 404


def test_upload_rejects_non_media_and_keeps_media(server, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    port, _ = server
    assert call(port, "POST /upload?name=run.exe", body=b"MZ")[0] == 400
    status, raw = call(port, "POST /upload?name=clip.mp4&target=en&mode=srt",
                       body=b"\x00" * 10)
    assert status == 200 and json.loads(raw)["target"] == "en"
    assert list((tmp_path / "uploads").rglob("clip.mp4"))


def test_safe_name_strips_paths_and_odd_characters() -> None:
    assert safe_name("..\\..\\Windows\\evil.mp4") == "evil.mp4"
    assert safe_name("مقطع <رائع>.MKV") == "مقطع _رائع_.mkv"
    assert safe_name("notes.txt") is None


def test_failures_carry_a_reason_people_can_act_on() -> None:
    from tarjim.gemini_client import QuotaExhausted
    from tarjim.server.jobs import classify

    assert classify(QuotaExhausted("used up")) == "quota"
    assert classify(RuntimeError("Gemini API key missing")) == "key"
    assert classify(FileNotFoundError("ffmpeg not found; install it")) == "tools"
    assert classify(ValueError("something odd")) == "unknown"


def test_only_a_failed_job_can_be_retried() -> None:
    from tarjim.server.jobs import Order

    def fail(_task: Task) -> None:
        raise RuntimeError("boom")

    board = Board(fail)
    task = board.submit(Order("https://example.com/v", target="en"))
    for _ in range(50):
        if task.finished:
            break
        time.sleep(0.02)
    again = board.retry(task.id)
    assert again is not None and again.id != task.id and again.order.target == "en"
    assert board.retry("000000000000") is None

def test_key_status_never_reveals_keys_and_bad_keys_are_refused(server) -> None:  # type: ignore[no-untyped-def]
    port, _ = server
    status, raw = call(port, "GET /keys")
    assert status == 200 and set(json.loads(raw)) == {"gemini", "fish"}
    assert all(isinstance(v, bool) for v in json.loads(raw).values())
    body = json.dumps({"provider": "gemini", "key": "short"}).encode()
    status, raw = call(port, "POST /keys", body=body, headers={"Content-Type": "application/json"})
    assert status == 400 and json.loads(raw)["result"] == "shape"
    assert call(port, "GET /keys", headers={"X-Tarjim-Token": "wrong"})[0] == 403


def test_key_shape_rules() -> None:
    from tarjim.keys import store, well_formed

    assert well_formed("AIzaSyA1234567890abcdefghij")
    assert not well_formed("has space in it 1234567")
    assert store("openai", "AIzaSyA1234567890abcdefghij") == "shape"
