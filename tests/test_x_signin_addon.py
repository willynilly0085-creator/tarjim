"""The add-on's side of the person's own X sign-in (2026-11-25): nothing is read before they allow
it, only x.com's cookies are read, only their name, value and place are sent, and only to their own
tarjim; the settings group gives the permission back."""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import tarjim
from tarjim.extension_home import for_firefox

EXTENSION = Path(tarjim.__file__).resolve().parent / "extension"
NODE = shutil.which("node")
CHECK = Path(__file__).with_name("x_signin.mjs")


@pytest.fixture(scope="module")
def seen() -> dict[str, Any]:
    if not NODE:
        pytest.skip("needs node")
    done = subprocess.run([NODE, str(CHECK), (EXTENSION / "xsignin.js").as_uri()],
                          capture_output=True, text=True, check=True, timeout=120, encoding="utf-8")
    found: dict[str, Any] = json.loads(done.stdout)
    return found


def test_only_a_post_x_refused_gets_the_button(seen: dict[str, Any]) -> None:
    assert seen["otherFailure"] == 0


def test_refused_permission_reads_and_sends_nothing(seen: dict[str, Any]) -> None:
    assert seen["denied"] == ["[xSigninButton]", 0, 0, False, ["[xSigninDenied]", ""]]


def test_allowed_it_reads_x_com_only_and_sends_only_the_cookie_itself(seen: dict[str, Any]) -> None:
    asked, read, sent, refreshed, note, pending = seen["sent"]
    assert asked == {"permissions": ["cookies"], "origins": ["https://x.com/*"]}
    assert read == [{"domain": "x.com"}]
    assert sent["url"] == f"http://tarjim.test/retry/{'a' * 12}/x-signin"
    assert sent["body"]["cookies"][0] == {"name": "auth_token", "value": "secret",
                                          "domain": ".x.com", "path": "/", "secure": True}
    assert refreshed == 1 and note == ["[xSigninSent]", ""] and not pending


def test_without_x_s_sign_in_cookie_nothing_is_sent(seen: dict[str, Any]) -> None:
    assert seen["none"] == [1, ["[xSigninNone]", "problem"]]


def test_an_old_waiting_press_is_dropped_unsent(seen: dict[str, Any]) -> None:
    assert seen["stale"] == ["", 1, False]


def test_settings_show_it_only_while_allowed_and_stop_gives_it_back(seen: dict[str, Any]) -> None:
    assert seen["shown"] is False and seen["hiddenAfter"] is True
    removed, note, stop_hidden = seen["stopped"]
    assert {"permissions": ["cookies"]} in removed and note == "[xSigninStopped]" and stop_hidden


def test_the_permission_is_optional_in_both_browsers() -> None:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    assert "cookies" not in manifest["permissions"]
    assert manifest["optional_permissions"] == ["cookies"]
    assert for_firefox(manifest)["optional_permissions"] == ["cookies"]
