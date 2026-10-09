"""What a stranger on the same computer, another local page, or a bad moment on disk cannot do."""
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from test_server import TOKEN, call, server  # noqa: F401

from tarjim import config, tools
from tarjim.engines import local_programs
from tarjim.server import housekeeping
from tarjim.server.jobs import Order, Task

PAGE = {"X-Tarjim-Token": ""}


def test_the_page_cookie_is_not_the_token_and_works_only_from_the_page(server) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    import http.client

    port, _ = server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/")
    page = conn.getresponse()
    page.read()
    session = (page.getheader("Set-Cookie") or "").split(";")[0]
    assert session and TOKEN not in session
    cookie = {**PAGE, "Cookie": session}
    assert call(port, "GET /jobs", headers={**cookie, "Sec-Fetch-Site": "same-origin"})[0] == 200
    assert call(port, "GET /jobs", headers={**cookie, "Sec-Fetch-Site": "none"})[0] == 200
    assert call(port, "GET /jobs", headers={
        **cookie, "Referer": f"http://127.0.0.1:{port}/"})[0] == 200
    assert call(port, "GET /jobs", headers=cookie)[0] == 403
    other_port = {**cookie, "Sec-Fetch-Site": "same-site"}
    assert call(port, "GET /translate?url=https://example.com/v", headers=other_port)[0] == 403
    stolen = {"X-Tarjim-Token": session.split("=", 1)[1]}
    assert call(port, "GET /jobs", headers=stolen)[0] == 403


def test_a_cut_off_upload_is_refused_and_leaves_nothing(server, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]  # noqa: F811
    import socket

    port, _ = server
    with socket.create_connection(("127.0.0.1", port), timeout=5) as line:
        line.sendall(b"POST /upload?name=clip.mp4 HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                     b"X-Tarjim-Token: " + TOKEN.encode() + b"\r\nContent-Length: 100\r\n\r\nabc")
        line.shutdown(socket.SHUT_WR)
        reply = line.recv(200)
    assert b" 400 " in reply and not list((tmp_path / "uploads").rglob("clip.mp4"))
    assert call(port, "POST /jobs", headers={"Content-Length": "many"})[0] == 400


def test_a_failed_job_shows_only_the_masked_reason() -> None:
    task = Task(Order("https://example.com/v"))
    task.stage, task.error = "failed", "401: key sk-abcdefghijklmnopqrstuvwxyz123456 rejected"
    shown = task.view()
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in json.dumps(shown)


def test_a_program_on_a_network_share_is_never_remembered(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    assert local_programs.remember(r"\\host\share\ollama.exe") == ""
    assert local_programs.remember("//host/share/ollama") == ""
    assert local_programs.remember("ollama.exe") == ""


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(config, "PAUSE", 0.0)
    return tmp_path


def test_settings_that_cannot_be_read_right_now_are_not_replaced(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config.save("ui_language", "ar")

    def locked(*_args: Any, **_kwargs: Any) -> str:
        raise PermissionError("in use")

    monkeypatch.setattr(Path, "read_text", locked)
    with pytest.raises(OSError):
        config.save("phone_mode", "srt")
    monkeypatch.undo()
    assert json.loads((home / "config.json").read_text(encoding="utf-8")) == {"ui_language": "ar"}


def test_a_damaged_settings_file_is_set_aside_not_lost(home: Path) -> None:
    (home / "config.json").write_text('{"ui_language": "ar"', encoding="utf-8")
    config.save("phone_mode", "srt")
    assert config.setting("phone_mode") == "srt"
    assert (home / "config.broken.json").read_text(encoding="utf-8") == '{"ui_language": "ar"'


def test_two_downloads_at_once_leave_the_engine_offline_again() -> None:
    from huggingface_hub import constants

    first_in, second_out, seen = threading.Event(), threading.Event(), []

    def first() -> None:
        with tools.online():
            first_in.set()
            second_out.wait(2)

    def second() -> None:
        first_in.wait(2)
        with tools.online():
            pass
        seen.append(constants.HF_HUB_OFFLINE)
        second_out.set()

    before, constants.HF_HUB_OFFLINE = constants.HF_HUB_OFFLINE, True
    threads = [threading.Thread(target=f) for f in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(3)
    after, constants.HF_HUB_OFFLINE = constants.HF_HUB_OFFLINE, before
    assert seen == [False] and after is True


def test_old_copies_of_videos_are_cleared_and_recent_ones_kept(tmp_path: Path) -> None:
    old, fresh = tmp_path / "uploads" / "old", tmp_path / "uploads" / "fresh"
    for folder in (old, fresh):
        folder.mkdir(parents=True)
        (folder / "clip.mp4").write_bytes(b"x")
    long_ago = time.time() - 8 * 24 * 3600
    os.utime(old / "clip.mp4", (long_ago, long_ago))
    os.utime(old, (long_ago, long_ago))
    housekeeping.sweep([tmp_path / "uploads", tmp_path / "missing"])
    assert not old.exists() and (fresh / "clip.mp4").exists()
