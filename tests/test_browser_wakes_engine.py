"""The browser extension can start a stopped engine through the program tarjim registers."""
import io
import json
import sys
from pathlib import Path

import pytest

from tarjim import native_host, native_setup

ORIGIN = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"


def framed(payload: dict[str, object]) -> io.BytesIO:
    body = json.dumps(payload).encode()
    return io.BytesIO(native_host.LENGTH.pack(len(body)) + body)


def test_a_message_is_read_and_answered_in_the_browsers_framing() -> None:
    assert native_host.read_message(framed({"wake": True})) == {"wake": True}
    out = io.BytesIO()
    native_host.write_message(out, {"started": True})
    size = native_host.LENGTH.unpack(out.getvalue()[:4])[0]
    assert json.loads(out.getvalue()[4:4 + size]) == {"started": True}


def test_an_oversized_or_broken_message_is_ignored() -> None:
    huge = io.BytesIO(native_host.LENGTH.pack(10**6) + b"x")
    assert native_host.read_message(huge) == {}
    assert native_host.read_message(io.BytesIO(b"\x01")) == {}


def test_a_stopped_engine_is_started_and_a_running_one_left_alone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import wake

    started: list[bool] = []
    monkeypatch.setattr(wake, "start", lambda: started.append(True) or True)
    monkeypatch.setattr(wake, "answers", lambda _page: False)
    assert native_host.answer({"wake": True}) == {"started": True}
    monkeypatch.setattr(wake, "answers", lambda _page: True)
    assert native_host.answer({"wake": True}) == {"running": True}
    assert native_host.answer({"anything": 1}) == {"error": "unknown"}
    assert started == [True]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    saved: dict[str, str] = {}
    monkeypatch.setattr(native_setup, "HOME", tmp_path)
    monkeypatch.setattr(native_setup, "setting", lambda name: saved.get(name, ""))
    monkeypatch.setattr(native_setup, "save", saved.__setitem__)
    monkeypatch.setattr(native_setup, "point_browsers", lambda path: None)
    monkeypatch.setattr(native_setup, "KNOWN", set())
    return tmp_path


def test_only_extensions_that_used_the_key_may_start_the_engine(home: Path) -> None:
    native_setup.remember("https://evil.example")
    native_setup.remember("")
    assert not (home / "native").exists()
    native_setup.remember(ORIGIN)
    written = json.loads((home / "native" / f"{native_setup.NAME}.json").read_text("utf-8"))
    assert written["allowed_origins"] == [f"{ORIGIN}/"]
    assert written["type"] == "stdio" and Path(written["path"]).is_file()
    launcher = Path(written["path"]).read_text(encoding="utf-8")
    assert "-P -m tarjim.native_host" in launcher
    if sys.platform == "win32":
        assert "python.exe" in launcher and "pythonw" not in launcher


def test_firefox_may_start_the_engine_once_its_add_on_was_allowed(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-12: Firefox knows the add-on by its own name, and is told of it only after a
    Firefox add-on reached the engine with the key."""
    from tarjim.extension_home import GECKO_ID

    pointed: list[Path] = []
    monkeypatch.setattr(native_setup, "point_firefox", pointed.append)
    native_setup.remember(ORIGIN)
    assert pointed == []  # a Chrome extension alone tells Firefox nothing
    native_setup.remember("moz-extension://0f3a6c1e-1111-4222-8333-444455556666")
    written = json.loads(pointed[0].read_text(encoding="utf-8"))
    assert written["allowed_extensions"] == [GECKO_ID] and "allowed_origins" not in written
    assert written["name"] == native_setup.NAME and Path(written["path"]).is_file()
    chrome = json.loads((home / "native" / f"{native_setup.NAME}.json").read_text("utf-8"))
    assert chrome["allowed_origins"] == [f"{ORIGIN}/"]  # and Chrome's list holds only Chrome's
