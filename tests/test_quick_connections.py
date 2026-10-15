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


def test_the_gemini_list_shows_text_models_only() -> None:
    from tarjim.engines.model_catalog import describe

    rows = [("gemini-3.8-flash", "Gemini 3.8 Flash", ""), ("lyria-3.5", "Lyria 3.5", ""),
            ("gemini-nano-banana-2.1", "Nano Banana 2.1", ""),
            ("gemini-robotics-er-2-preview", "Gemini Robotics-ER 2", ""),
            ("antigravity-preview-latest", "Antigravity Agent", ""),
            ("gemini-3.1-pro-preview-customtools", "Gemini 3.1 Pro Custom Tools", ""),
            ("gemini-omni-1.1-flash", "Gemini Omni 1.1 Flash", "")]
    assert [m["id"] for m in describe(rows)] == ["gemini-3.8-flash"]
