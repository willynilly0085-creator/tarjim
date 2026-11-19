"""The extension translates the text a person selects on a page, through their own tarjim."""
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import tarjim
from tarjim import text

EXTENSION = Path(tarjim.__file__).resolve().parent / "extension"
NODE = shutil.which("node")
CHECK = Path(__file__).with_name("selected_text.mjs")
PAGE = Path(__file__).with_name("selection_page.mjs")


@pytest.fixture(scope="module")
def seen() -> dict[str, Any]:
    if not NODE:
        pytest.skip("needs node")
    done = subprocess.run([NODE, str(CHECK), (EXTENSION / "textcard.js").as_uri()],
                          capture_output=True, text=True, check=True, timeout=120, encoding="utf-8")
    found: dict[str, Any] = json.loads(done.stdout)
    return found


def test_the_selection_goes_to_the_persons_own_tarjim_with_their_language(
        seen: dict[str, Any]) -> None:
    assert seen["good"] == {"translation": "hello"}
    assert seen["sent"] == {"url": "http://tarjim.test/text", "token": "key",
                            "body": {"text": "selected", "target": "ar", "other": ""}}


def test_a_failure_is_said_in_the_persons_words(seen: dict[str, Any]) -> None:
    assert seen["quota"] == {"message": "[errQuota]"}
    assert seen["long"] == {"message": "[textLong]"}
    assert seen["unpaired"] == {"message": "[pairTitle]"}


def test_after_an_update_the_open_pages_get_the_new_page_script(seen: dict[str, Any]) -> None:
    """A page open while the add-on updated kept only the old copy, cut off from the add-on,
    so "as I select" stopped working there until the page was reloaded (2026-11-19)."""
    assert seen["updatedMenu"] == [0, 0]  # the right-click menu puts the script in itself
    assert seen["updated"] == [2, [[{"tabId": 1, "allFrames": True}, ["selection.js"]],
                                   [{"tabId": 3, "allFrames": True}, ["selection.js"]]]]


def test_a_stopped_tarjim_is_started_before_the_selection_is_given_up(
        seen: dict[str, Any]) -> None:
    assert seen["woken"] == [{"translation": "woken"}, 1]


def test_the_card_gets_its_words_in_the_persons_language(seen: dict[str, Any]) -> None:
    assert seen["words"] == {"working": "[textWorking]", "copy": "[copy]", "copied": "[copied]",
                             "ask": "[textAsk]", "long": "[textLong]", "dir": "rtl"}
    assert seen["other"] is False


def test_no_page_is_watched_until_the_person_asks_and_the_browser_allows(
        seen: dict[str, Any]) -> None:
    assert seen["menuOnly"] == [False, 0]
    assert seen["refused"] == [False, "menu", 0]
    assert seen["allowed"] == [True, "card", [[["selection.js"], ["<all_urls>"]]]]
    assert seen["back"] == [True, "menu", 1]


def test_a_right_click_puts_the_card_in_the_frame_that_was_clicked(seen: dict[str, Any]) -> None:
    shown, injected, told = seen["shown"]
    assert shown is True
    assert injected == {"target": {"tabId": 4, "frameIds": [2]}, "files": ["selection.js"]}
    assert told == [4, {"type": "tarjim-selection", "text": "picked"}, {"frameId": 2}]
    assert seen["closed"] is False  # a page the browser keeps extensions out of


def test_translations_nobody_clicked_for_are_held_to_a_few_a_minute(seen: dict[str, Any]) -> None:
    assert seen["unasked"] == [10, {"ask": True}]
    assert seen["clicked"] == {"translation": "t"}  # a click is never held back
    assert seen["later"] == {"translation": "t"}


@pytest.fixture(scope="module")
def page() -> dict[str, Any]:
    if not NODE:
        pytest.skip("needs node")
    done = subprocess.run([NODE, str(PAGE), (EXTENSION / "selection.js").as_uri()],
                          capture_output=True, text=True, check=True, timeout=120, encoding="utf-8")
    found: dict[str, Any] = json.loads(done.stdout)
    return found


def test_a_page_cannot_make_up_the_persons_selecting(page: dict[str, Any]) -> None:
    assert page["madeUp"] == [0, 0]
    assert page["own"] == [[{"type": "tarjim-text", "text": "some text", "auto": True}],
                           ["done", None]]


def test_a_held_translation_waits_for_the_persons_own_click(page: dict[str, Any]) -> None:
    assert page["held"] == [{"type": "tarjim-text", "text": "other text", "auto": True},
                            "card ask", "button"]
    assert page["fakeClick"] == 2
    assert page["click"] == [{"type": "tarjim-text", "text": "other text", "auto": False},
                             "clicked"]
    assert page["button"] == [3, "card ask"]  # "a button by the text" sends nothing by itself


def test_a_page_left_with_an_updated_add_ons_old_script_stays_quiet(
        page: dict[str, Any]) -> None:
    """Seen 2026-11-19 in the owner's Chrome: "Extension context invalidated", thrown by the old
    copy of selection.js on a page that stayed open while the add-on updated itself."""
    assert page["orphan"] == [[], 0, [0, 0, 0, 0]]  # no error, no card, nothing listened to
    assert page["again"] == [[1, 1, 1, 1], "fifth text", []]


def test_the_manifest_asks_for_every_page_only_as_an_option() -> None:
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["optional_host_permissions"] == ["<all_urls>"]
    assert manifest["host_permissions"] == ["http://127.0.0.1/*", "http://localhost/*"]
    assert "content_scripts" not in manifest
    assert manifest["commands"]["translate-selection"]["description"] == "__MSG_textMenu__"


def test_the_page_script_stands_alone_and_knows_the_engines_limit() -> None:
    script = (EXTENSION / "selection.js").read_text(encoding="utf-8")
    assert "import " not in script and "innerHTML" not in script
    assert f"const MOST = {text.MOST};" in script
    assert "mode: \"closed\"" in script and "prefers-reduced-motion" in script
