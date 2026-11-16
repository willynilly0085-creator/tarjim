"""Selected text has its own engine and model, apart from the videos'; unset, the soonest one."""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from tarjim import assistant_settings, config, text, text_engine
from tarjim.engines import choice, provider_models
from tarjim.server.app import Handler
from tarjim.server.jobs import Board

TOKEN = "secret-token"


@pytest.fixture(autouse=True)
def own_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(text_engine, "works", lambda provider, _server: provider != "grok")
    monkeypatch.setattr(text_engine, "LIGHT", {})


def test_nothing_picked_means_tarjim_picks() -> None:
    assert text_engine.over() == {}
    assert text_engine.view() == {"provider": "", "model": "", "server": "", "name": "",
                                  "label": ""}


def test_a_picked_engine_and_model_are_kept_apart_from_the_videos() -> None:
    config.save("translate_provider", "antigravity")
    config.save("gemini_model", "gemini-4-carbon")
    assert text_engine.remember({"provider": "gemini", "model": "gemini-3.8-flash"})
    assert text_engine.over() == {"translate_provider": "gemini",
                                  "gemini_model": "gemini-3.8-flash"}
    seen = text_engine.view()
    assert (seen["provider"], seen["name"], seen["model"]) == (
        "gemini", "Google Gemini", "gemini-3.8-flash")
    assert config.setting("translate_provider") == "antigravity"
    assert config.setting("gemini_model") == "gemini-4-carbon"


def test_an_ai_on_this_computer_is_picked_with_its_program_and_model() -> None:
    assert text_engine.remember({"provider": "local", "server": "lmstudio", "model": "aya:8b"})
    assert text_engine.over() == {"translate_provider": "local", "local_server": "lmstudio",
                                  "local_model": "aya:8b"}


def test_a_choice_that_cannot_work_or_is_not_a_model_name_is_not_kept() -> None:
    assert not text_engine.remember({"provider": "grok"})
    assert not text_engine.remember({"provider": "nobody"})
    assert not text_engine.remember({"provider": "gemini", "model": "x; rm -rf"})
    assert text_engine.over() == {}


def test_an_empty_choice_goes_back_to_automatic() -> None:
    assert text_engine.remember({"provider": "gemini", "model": "gemini-3.8-flash"})
    assert text_engine.remember({"provider": ""})
    assert text_engine.over() == {} and config.setting("text_model") == ""


class Reads:
    """An engine that notes the settings it finds while it is asked."""
    hears = False

    def __init__(self) -> None:
        self.found: list[tuple[str, str]] = []

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.found.append((config.setting("translate_provider"), config.setting("openai_model")))
        return {"translation": "done"}


def test_the_picked_engine_is_asked_as_picked_and_the_videos_settings_come_back(
        monkeypatch: pytest.MonkeyPatch) -> None:
    engine, asked = Reads(), []
    config.save("translate_provider", "claude")
    monkeypatch.setattr(choice, "asker", lambda provider: asked.append(provider) or engine)
    monkeypatch.setattr(choice, "usable", lambda _provider, _role: False)
    monkeypatch.setattr(choice, "soonest", lambda: pytest.fail("tarjim was not to pick"))
    assert text_engine.remember({"provider": "openai", "model": "gpt-6-luna"})
    assert text.translated("hello", "ar") == ("done", "openai")
    assert asked == ["openai"] and engine.found == [("openai", "gpt-6-luna")]
    assert config.setting("translate_provider") == "claude"
    assert config.setting("openai_model") == ""


def test_automatic_asks_an_engine_with_a_key_for_its_lightest_model(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Measured 2026-11-16 with the owner's key on four texts: Gemini 4 Hydrogen answered in
    3.4 to 9.0 s and 3.8 Flash in 1.5 to 4.0 s, and automatic asked whichever the videos use."""
    engine, listed = Reads(), []
    config.save("translate_provider", "openai")
    config.save("openai_model", "gpt-6.1-sol")
    monkeypatch.setattr(provider_models, "models_for", lambda provider: listed.append(provider) or [
        {"id": "gpt-6.1-sol", "suggested": ""}, {"id": "gpt-6-luna", "suggested": "yes"}])
    monkeypatch.setattr(choice, "asker", lambda _provider: engine)
    monkeypatch.setattr(choice, "soonest", lambda: ["openai"])
    monkeypatch.setattr(choice, "usable", lambda _provider, _role: False)
    assert text.translated("hello", "ar") == text.translated("again", "ar") == ("done", "openai")
    assert engine.found == [("openai", "gpt-6-luna")] * 2
    assert listed == ["openai"]  # the list is a request of its own: asked once, then kept
    assert config.setting("openai_model") == "gpt-6.1-sol"


def test_only_an_engine_with_a_key_and_a_suggested_model_is_asked_for_a_lighter_one(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(provider_models, "models_for", lambda _p: [{"id": "m", "suggested": ""}])
    assert text_engine.lighter("openai") == {}  # nothing known: the picked model stays
    monkeypatch.setattr(provider_models, "models_for", lambda _p: [{"id": "m", "suggested": "yes"}])
    assert text_engine.lighter("openai") == {"openai_model": "m"}  # an empty answer is not kept
    for other in ("claude", "local", "custom", "nobody"):
        assert text_engine.lighter(other) == {}


def test_settings_held_on_one_thread_are_not_seen_on_another() -> None:
    seen: list[str] = []
    with config.using({"translate_provider": "openai"}):
        other = threading.Thread(target=lambda: seen.append(config.setting("translate_provider")))
        other.start()
        other.join()
        assert config.setting("translate_provider") == "openai"
    assert seen == [""] and config.setting("translate_provider") == ""


@pytest.fixture
def port(tmp_path: Path):  # type: ignore[no-untyped-def]
    Handler.board, Handler.token = Board(lambda _task: None), TOKEN
    Handler.uploads = tmp_path / "uploads"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def asked_of(port: int, path: str, body: Any = None) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST" if body is not None else "GET", path,
                 body=json.dumps(body).encode() if body is not None else None,
                 headers={"X-Tarjim-Token": TOKEN, "Content-Type": "application/json"})
    response = conn.getresponse()
    return response.status, json.loads(response.read())


def test_the_page_reads_and_saves_the_choice(port: int) -> None:
    assert asked_of(port, "/text")[1]["provider"] == ""
    code, saved = asked_of(port, "/text/use", {"provider": "gemini", "model": "gemini-3.8-flash"})
    assert code == 200 and saved["label"] and saved["name"] == "Google Gemini"
    assert asked_of(port, "/text")[1] == saved
    assert asked_of(port, "/text/use", {"provider": "grok"}) == (400, {"error": "unusable"})
    assert asked_of(port, "/text")[1] == saved  # a refused choice changes nothing


def test_a_chat_can_read_and_change_who_translates_text(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, Any]] = []
    monkeypatch.setattr(assistant_settings, "call",
                        lambda path, body=None: seen.append((path, body)))
    assistant_settings.selected_text_translator()
    assistant_settings.selected_text_translator("auto")
    assistant_settings.selected_text_translator("gemini", "gemini-3.8-flash")
    assert seen == [("/text", None),
                    ("/text/use", {"provider": "", "model": "", "server": ""}),
                    ("/text/use", {"provider": "gemini", "model": "gemini-3.8-flash",
                                   "server": ""})]
