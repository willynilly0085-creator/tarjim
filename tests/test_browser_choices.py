"""The add-on's choices are kept by the engine, so a browser added later starts with them."""
import http.client
import json
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import tarjim
from tarjim import browser_choices, config
from tarjim.server.app import Handler
from tarjim.server.jobs import Board

TOKEN = "secret-token"
NODE = shutil.which("node")
EXTENSION = Path(tarjim.__file__).resolve().parent / "extension"


@pytest.fixture(autouse=True)
def own_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def test_only_the_add_ons_own_choices_are_kept_as_plain_words() -> None:
    assert browser_choices.read() == {}
    kept = browser_choices.remember({"target": "ar", "dialect": "msa", "token": "secret",
                                     "voice": "<script>", "mode": 3, "textMode": "button"})
    assert kept == {"target": "ar", "dialect": "msa", "textMode": "button"}
    assert browser_choices.remember({"voice": "studio"}) == {**kept, "voice": "studio"}


@pytest.fixture
def port(tmp_path: Path):  # type: ignore[no-untyped-def]
    Handler.board, Handler.token, Handler.uploads = Board(lambda _t: None), TOKEN, tmp_path / "up"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()


def asked(port: int, method: str, body: Any = None) -> tuple[int, Any]:
    link = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    link.request(method, "/browser", json.dumps(body) if body is not None else None,
                 {"X-Tarjim-Token": TOKEN, "Content-Type": "application/json"})
    reply = link.getresponse()
    return reply.status, json.loads(reply.read())


def test_the_add_on_saves_and_reads_its_choices_through_the_engine(port: int) -> None:
    assert asked(port, "GET") == (200, {})
    assert asked(port, "POST", {"voice": "studio", "server": "elsewhere"}) == (
        200, {"voice": "studio"})
    assert asked(port, "GET") == (200, {"voice": "studio"})


@pytest.fixture(scope="module")
def shared() -> dict[str, Any]:
    if not NODE:
        pytest.skip("needs node")
    done = subprocess.run([NODE, str(Path(__file__).with_name("browser_choices.mjs")),
                           (EXTENSION / "pairing.js").as_uri()],
                          capture_output=True, text=True, check=True, timeout=120,
                          encoding="utf-8")
    found: dict[str, Any] = json.loads(done.stdout)
    return found


def test_a_browser_that_joins_takes_what_the_engine_kept(shared: dict[str, Any]) -> None:
    assert shared["joined"] == {"dialect": "msa", "textMode": "button", "voice": "studio",
                                "shared": True, "posted": []}
    assert shared["again"] == {"posted": []}  # taken once; the person's own choices stay theirs


def test_the_first_browser_gives_the_engine_its_choices(shared: dict[str, Any]) -> None:
    assert shared["first"] == {"posted": [{"target": "ar", "dialect": "saudi", "mode": "burn",
                                           "voice": "gemini", "textMode": "menu",
                                           "textOther": ""}]}


def test_each_choice_saved_in_the_add_on_goes_to_the_engine(shared: dict[str, Any]) -> None:
    assert shared["saved"] == [{"voice": "eleven"}]
    assert shared["unshared"] == []  # the pairing key and other private values stay put
