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
