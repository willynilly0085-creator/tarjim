"""The tarjim shortcut brings back a stopped engine: it starts it once, waits until it answers and
opens its page; a running engine only gets its page opened."""
import os
import socket
import time
from pathlib import Path
from typing import Any

import pytest

from tarjim import wake


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    pages: list[str] = []
    monkeypatch.setattr(wake.webbrowser, "open", pages.append)
    monkeypatch.setattr(wake, "HOME", tmp_path)
    monkeypatch.setattr(wake, "STARTING", tmp_path / "waking")
    return pages


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    commands: list[list[str]] = []
    monkeypatch.setattr(wake, "start_detached",
                        lambda command, log: commands.append(command) or True)
    return commands


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_nothing_listening_does_not_answer() -> None:
    assert not wake.answers(f"http://127.0.0.1:{free_port()}")


def test_a_running_engine_only_gets_its_page_opened(
        monkeypatch: pytest.MonkeyPatch, opened: list[str], started: list[list[str]]) -> None:
    monkeypatch.setattr(wake, "answers", lambda page: True)
    assert wake.main(["--port", "17699"]) == 0
    assert opened == ["http://127.0.0.1:17699/"] and started == []


def test_a_stopped_engine_is_started_once_then_its_page_opens(
        monkeypatch: pytest.MonkeyPatch, opened: list[str], started: list[list[str]]) -> None:
    monkeypatch.setattr(wake, "answers", lambda page: bool(started))
    monkeypatch.setattr(wake.time, "sleep", lambda seconds: None)
    assert wake.main(["--port", "17699"]) == 0
    assert len(started) == 1 and opened == ["http://127.0.0.1:17699/"]
    command = started[0]
    assert command[1:4] == ["-P", "-m", "tarjim.server"] and command[-2:] == ["--port", "17699"]


def test_the_shortcut_starts_the_engine_on_its_usual_port(
        monkeypatch: pytest.MonkeyPatch, opened: list[str], started: list[list[str]]) -> None:
    monkeypatch.setattr(wake, "answers", lambda page: bool(started))
    monkeypatch.setattr(wake, "setting", lambda name: "")
    monkeypatch.setattr(wake.time, "sleep", lambda seconds: None)
    assert wake.main([]) == 0
    assert "--port" not in started[0] and opened == [f"{wake.SERVER}/"]


def test_a_second_double_click_while_it_starts_does_not_start_another(
        opened: list[str], started: list[list[str]]) -> None:
    assert wake.start(17699) and not wake.start(17699)
    assert len(started) == 1


def test_an_old_start_does_not_block_a_new_one(opened: list[str], started: list[list[str]]) -> None:
    wake.STARTING.touch()
    old = time.time() - wake.WAIT - 1
    os.utime(wake.STARTING, (old, old))
    assert wake.start()
    assert len(started) == 1


def test_an_engine_that_never_answers_still_opens_the_page_and_says_so(
        monkeypatch: pytest.MonkeyPatch, opened: list[str], started: list[list[str]]) -> None:
    monkeypatch.setattr(wake, "answers", lambda page: False)
    monkeypatch.setattr(wake, "WAIT", 0.0)
    monkeypatch.setattr(wake, "wait", lambda page: False)
    assert wake.main(["--port", "17699"]) == 1
    assert opened == ["http://127.0.0.1:17699/"] and len(started) == 1


def test_waiting_gives_up_after_its_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(wake, "answers", lambda page: calls.append(page) and False)
    assert not wake.wait("http://127.0.0.1:1", seconds=0.05, tick=0.01)
    assert calls
