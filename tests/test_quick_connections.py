import socket
import time

import pytest

from tarjim.engines import local_servers, provider_models
from tarjim.onboarding import scan


def test_a_programs_model_list_is_asked_once_until_a_fresh_scan(
        monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    def listing() -> list[provider_models.Model]:
        asked.append("antigravity")
        return []

    monkeypatch.setitem(provider_models.OWN_LISTS, "antigravity", listing)
    monkeypatch.setattr(provider_models, "KEPT", {})
    monkeypatch.setattr(scan, "SECTIONS", ("device",))
    monkeypatch.setattr(scan, "section", lambda name, fresh=False: {})
    provider_models.models_for("antigravity")
    provider_models.models_for("antigravity")
    assert asked == ["antigravity"]
    scan.everything(fresh=True)
    provider_models.models_for("antigravity")
    assert asked == ["antigravity", "antigravity"]


def test_a_closed_local_port_is_given_up_on_at_once() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    started = time.monotonic()
    assert not local_servers.answering(f"http://127.0.0.1:{port}")
    assert time.monotonic() - started < 1.0


def test_a_listening_local_program_is_found() -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        assert local_servers.answering(f"http://127.0.0.1:{server.getsockname()[1]}")
