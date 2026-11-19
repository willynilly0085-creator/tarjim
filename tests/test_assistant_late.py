"""A chat tool whose engine answers late says so in words, and waits as long as its work needs.

Seen 2026-11-16: test_setup failed twice with "Error executing tool test_setup" and nothing else,
while /setup/selftest asked directly answered {"ok": true} after 18 to 47 seconds (Gemini 4
Hydrogen by key). The tool read with a 30-second limit, and a read that runs out of time raises
a bare TimeoutError, which went out of the tool unexplained."""
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from tarjim import assistant, assistant_http, assistant_settings
from tarjim.engines import antigravity, local_programs, sign_in, web
from tarjim.fetch import LOOK_SECONDS

LATE_BY = 1.5


class Late(BaseHTTPRequestHandler):
    def answer(self) -> None:
        time.sleep(LATE_BY)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    do_GET = do_POST = answer

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def late(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Late)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    where = {"server": f"http://127.0.0.1:{server.server_address[1]}", "token": "t"}
    monkeypatch.setattr(assistant_http, "setting", lambda name: where.get(name, ""))
    yield
    server.shutdown()
    server.server_close()


@pytest.mark.usefixtures("late")
def test_an_engine_that_answers_late_gets_words_not_an_error() -> None:
    said = assistant_http.call("/setup/selftest", {"language": "ar"}, wait=0.3)
    assert said["error"] == assistant_http.LATE and said["waited_seconds"] == 0.3
    assert "still working" in said["detail"] and assistant_http.AGAIN in said["detail"]
    assert assistant_http.call("/setup/selftest", {}, wait=LATE_BY + 5) == {"ok": True}
    assert assistant_http.fetch_text("/files/x/a.srt", wait=0.3)["error"] == assistant_http.LATE


@pytest.mark.usefixtures("late")
def test_the_self_test_says_what_to_do_when_the_ai_is_still_answering(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_settings, "AI", 0.3)
    said = assistant_settings.test_setup()
    assert said["error"] == assistant_http.LATE
    assert "test_setup again" in said["detail"] and "use_connection" in said["detail"]


def test_a_test_with_an_ai_waits_longer_than_the_engine_waits_for_the_ai() -> None:
    # A keyed engine gives up after web.TIMEOUT and the self-test then says why: the tool waits
    # past that, so the reason reaches the chat instead of a guess.
    assert assistant_http.AI > web.TIMEOUT > assistant_http.SLOW > assistant_http.SHORT


def test_work_that_asks_a_program_or_a_site_waits_past_its_own_limits() -> None:
    connections = sign_in.STATUS_SECONDS + antigravity.LIST_SECONDS  # every overview
    longest = max(LOOK_SECONDS, connections + local_programs.START_SECONDS,
                  connections + local_programs.SEARCH_SECONDS)
    assert longest < assistant_http.SLOW


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    seen: dict[str, float] = {}

    def call(path: str, body: Any = None, wait: float = assistant_http.SHORT,
             then: str = "") -> Any:
        seen[path.partition("?")[0]] = wait
        return {}

    for module in (assistant, assistant_settings):
        monkeypatch.setattr(module, "call", call)
    return seen


def test_each_tool_waits_as_long_as_what_it_asks(waits: dict[str, float]) -> None:
    assistant_settings.test_setup()
    for tool, args in ((assistant_settings.plan_setup, ()), (assistant_settings.apply_setup,
                       ({}, {})), (assistant_settings.install_subscription_app, ("claude",)),
                       (assistant_settings.start_local_ai, ("ollama",)),
                       (assistant_settings.find_local_ai, ()), (assistant_settings.list_models,
                       ("gemini",)), (assistant.list_connections, ()),
                       (assistant.use_connection, ("gemini",)), (assistant.list_languages, ()),
                       (assistant.translate_video, ("https://example.com/v",))):
        tool(*args)
    assert waits.pop("/setup/selftest") == assistant_http.AI
    assert waits.pop("/languages") == assistant_http.SHORT
    assert waits.pop("/jobs") == assistant_http.SHORT  # queued at once, nothing asked
    assert set(waits.values()) == {assistant_http.SLOW}, waits


def test_a_link_read_late_says_how_to_start_without_picking(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def call(path: str, body: Any = None, wait: float = 0, then: str = "") -> Any:
        assert path == "/links/qualities"
        return assistant_http.late(wait, then)

    monkeypatch.setattr(assistant, "call", call)
    said = assistant.translate_video("https://example.com/v")
    assert said["error"] == assistant_http.LATE and 'quality "default"' in said["detail"]
