"""The browser extension's popup, as the review of 2026-10-27 found it: it said where keys are
added, said why a press failed on the job itself, and never blamed Gemini for another provider."""
import json
from pathlib import Path

import pytest

from tarjim import config
from tarjim.server import voice_routes
from tarjim.ui_languages import codes

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
EXTENSION = ROOT / "extension"
PAGE = ROOT / "web"


def words(code: str) -> dict[str, str]:
    raw = json.loads((EXTENSION / "_locales" / code / "messages.json").read_text(encoding="utf-8"))
    return {key: entry["message"] for key, entry in raw.items()}


def source(name: str) -> str:
    return (EXTENSION / name).read_text(encoding="utf-8")


def test_the_translator_control_says_keys_go_on_the_page_and_opens_its_connect_part() -> None:
    page = (EXTENSION / "app.html").read_text(encoding="utf-8")
    assert 'id="open-keys"' in page and 'data-i18n="engineKeys"' in page
    assert 'openPage("#connect")' in source("engine.js")
    main = (PAGE / "main.js").read_text(encoding="utf-8")
    assert '"#connect": "connect"' in main and "preferKeys()" in main
    assert 'data-step="connect"' in (PAGE / "index.html").read_text(encoding="utf-8")


def test_key_and_quota_failures_name_no_provider_in_any_language() -> None:
    for code in codes():
        page = json.loads((PAGE / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
        mine = words(code)
        assert mine["errKey"] == page["err_key"], code
        assert mine["errQuota"] == page["err_quota"], code
        assert "Google" not in mine["keyChecking"] + mine["keyRejected"], code
        assert "Gemini" not in mine["errKey"] + mine["errQuota"], code


def test_arabic_calls_the_program_by_its_arabic_name() -> None:
    arabic = words("ar")
    shortcut = {"offlineWindows"}  # the file on the desktop is named tarjim
    named = [key for key, text in arabic.items() if "tarjim" in text and key not in shortcut]
    assert named == []


def test_a_failed_press_on_a_job_is_said_on_that_job() -> None:
    jobs = source("jobs.js")
    assert "guarded(row" in jobs and ".job-note" in jobs
    assert ".catch(() => null)" not in jobs  # remove no longer claims success when it failed


def test_a_translate_that_tarjim_refuses_says_why() -> None:
    assert "sendProblem(error, " in source("app.js")
    assert '"bad url": "sendBadLink"' in source("upload.js")


def test_auto_pairing_keeps_the_popup_and_its_code_on_screen() -> None:
    panels = source("panels.js")
    assert 'openPage("", false)' in panels and "requireInteraction: true" in panels


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("TARJIM_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("TARJIM_FISH_API_KEY", raising=False)
    return tmp_path


def test_voices_that_need_a_key_say_whether_it_is_there(home: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    view = voice_routes.view()
    assert view["gemini"]["has_key"] is False and view["fish"]["has_key"] is False
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-from-gemini-cli")  # the key translation also uses
    assert voice_routes.view()["gemini"]["has_key"] is True
    page = (EXTENSION / "app.html").read_text(encoding="utf-8")
    assert page.count('data-key="fish"') == 2 and page.count('data-key="gemini"') == 1
