"""Only one engine listens on the port; a second one leaves before starting anything."""
from http.server import BaseHTTPRequestHandler

import pytest

from tarjim.server.listener import Taken, take_port


def test_a_second_engine_cannot_take_the_same_port() -> None:
    first = take_port(0, BaseHTTPRequestHandler)
    try:
        with pytest.raises(Taken):
            take_port(first.server_address[1], BaseHTTPRequestHandler)
    finally:
        first.server_close()


def test_the_port_is_free_again_once_the_engine_closed() -> None:
    first = take_port(0, BaseHTTPRequestHandler)
    port = first.server_address[1]
    first.server_close()
    take_port(port, BaseHTTPRequestHandler).server_close()


def test_the_engine_says_why_it_closes(monkeypatch: pytest.MonkeyPatch,
                                       capsys: pytest.CaptureFixture[str]) -> None:
    from tarjim.server import engine

    def busy(*_args: object) -> object:
        raise Taken("port 1 is in use")

    monkeypatch.setattr(engine, "start_up", lambda: None)
    monkeypatch.setattr(engine, "token", lambda: "t")
    monkeypatch.setattr(engine, "take_port", busy)
    monkeypatch.setattr(engine, "run_alongside", lambda _port: pytest.fail("started anyway"))
    assert engine.main(["--port", "1"]) == 1
    assert "in use" in capsys.readouterr().out


def test_an_engine_that_replaces_another_keeps_asking_for_the_port(
        capsys: pytest.CaptureFixture[str]) -> None:
    """2026-11-14 and 2026-11-15: an engine restarted onto new code was refused the port within
    a second of its start and closed, and no engine was left running."""
    import os
    import threading

    first = take_port(0, BaseHTTPRequestHandler)
    port = first.server_address[1]
    threading.Timer(0.6, first.server_close).start()
    take_port(port, BaseHTTPRequestHandler, os.getpid()).server_close()
    said = capsys.readouterr().out
    assert f"replaces engine {os.getpid()}, which is still running" in said
    assert "was let go" in said


def test_an_engine_that_replaces_another_gives_up_in_the_end(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.server import listener

    monkeypatch.setattr(listener, "PATIENCE", 0.3)
    first = take_port(0, BaseHTTPRequestHandler)
    try:
        with pytest.raises(Taken):
            take_port(first.server_address[1], BaseHTTPRequestHandler, 1)
    finally:
        first.server_close()


def test_the_engine_tells_the_port_which_engine_it_replaces(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.server import engine

    asked: list[tuple[object, ...]] = []

    def busy(*args: object) -> object:
        asked.append(args)
        raise Taken("port 1 is in use")

    monkeypatch.setattr(engine, "start_up", lambda: None)
    monkeypatch.setattr(engine, "token", lambda: "t")
    monkeypatch.setattr(engine, "wait_for_exit", lambda _pid: None)
    monkeypatch.setattr(engine, "take_port", busy)
    assert engine.main(["--port", "1", "--after", "77"]) == 1
    assert asked == [(1, engine.Handler, 77)]
