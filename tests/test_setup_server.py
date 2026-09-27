import http.client
import json
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from tarjim import config
from tarjim.server import pages
from tarjim.server.app import Handler
from tarjim.server.jobs import Board
from tarjim.server.pairing import Pairing
from tarjim.tools import Shelf

TOKEN = "t" * 32
EXTENSION = "chrome-extension://abcdefghijklmnop"


@pytest.fixture
def port(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<p>tarjim</p>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setattr(pages, "WEB", web)
    monkeypatch.setattr(config, "HOME", tmp_path / "home")
    monkeypatch.setattr(config, "CONFIG", tmp_path / "home" / "config.json")
    Handler.board, Handler.token, Handler.uploads = Board(lambda _t: None), TOKEN, tmp_path
    Handler.shelf, Handler.pairing = Shelf(), Pairing()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def call(port: int, request: str, body: bytes = b"",
         headers: dict[str, str] | None = None) -> http.client.HTTPResponse:
    method, path = request.split(" ", 1)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    return conn.getresponse()


def test_page_sets_a_strict_session_cookie_and_cannot_be_framed(port: int) -> None:
    page = call(port, "GET /")
    cookie = page.getheader("Set-Cookie") or ""
    assert page.status == 200 and "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert "frame-ancestors 'none'" in (page.getheader("Content-Security-Policy") or "")
    session = cookie.split(";")[0]
    assert call(port, "GET /jobs", headers={"Cookie": session}).status == 200
    foreign = {"Cookie": session, "Origin": "https://evil.example"}
    assert call(port, "GET /jobs", headers=foreign).status == 403


def test_assets_never_leave_the_web_folder(port: int) -> None:
    assert call(port, "GET /web/index.html").status == 200
    assert call(port, "GET /web/../secret.txt").status == 404


def test_extension_pairs_only_after_the_person_allows_it_and_gets_the_token_once(port: int) -> None:
    assert call(port, "POST /pair", headers={"Origin": "https://evil.example"}).status == 403
    request_id = json.loads(call(port, "POST /pair", headers={"Origin": EXTENSION}).read())["id"]
    assert json.loads(call(port, f"GET /pair/{request_id}").read()) == {"state": "pending"}
    owner = {"X-Tarjim-Token": TOKEN}
    assert [p["id"] for p in json.loads(call(port, "GET /pairs", headers=owner).read())] == [
        request_id]
    assert call(port, f"POST /pairs/{request_id}/allow", headers=owner).status == 200
    first = json.loads(call(port, f"GET /pair/{request_id}").read())
    assert first == {"state": "allowed", "token": TOKEN}
    assert json.loads(call(port, f"GET /pair/{request_id}").read()) == {"state": "allowed"}


def test_setup_only_accepts_known_values(port: int) -> None:
    owner = {"X-Tarjim-Token": TOKEN, "Content-Type": "application/json"}
    body = json.dumps({"ui_language": "en", "translate_provider": "evil",
                       "listen_provider": "local"})
    state = json.loads(call(port, "POST /setup", body.encode(), owner).read())
    assert state["ui_language"] == "en" and state["listen_provider"] == "local"
    assert state["translate_provider"] == ""
