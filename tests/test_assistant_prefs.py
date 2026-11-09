"""A chat changes the person's own settings through the same routes and gate as the settings
page, hears each refusal's Arabic reason, and changes settings for one video alone
(2026-11-09)."""
import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from prefs_server import TOKEN, serving

from tarjim import assistant, assistant_http, assistant_prefs
from tarjim.server.jobs import Board

NEW_TOOLS = {"get_preferences", "change_preferences", "reset_preferences", "use_preset"}


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    seen: list[tuple[str, Any]] = []

    def call(path: str, body: Any = None) -> Any:
        seen.append((path, body))
        return {"ok": True}

    monkeypatch.setattr(assistant_prefs, "call", call)
    monkeypatch.setattr(assistant, "call", call)
    return seen


@pytest.fixture
def live(prefs_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    """The chat tools talking to a real tarjim server with a home of its own."""
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    with serving(Board(lambda _task: None), tmp_path / "uploads") as port:
        where = {"server": f"http://127.0.0.1:{port}", "token": TOKEN}
        monkeypatch.setattr(assistant_http, "setting", lambda name: where.get(name, ""))
        yield port


def test_the_settings_tools_are_offered_to_a_chat_with_short_descriptions() -> None:
    tools = {t.name: t for t in asyncio.run(assistant.tarjim.list_tools())}
    assert set(tools) >= NEW_TOOLS
    for name in NEW_TOOLS:
        assert len(tools[name].description or "") < 500, name
    assert len(tools["translate_video"].input_schema["properties"]) == 4


def test_each_tool_reaches_its_route(asked: list[tuple[str, Any]]) -> None:
    assistant_prefs.get_preferences()
    assistant_prefs.get_preferences("timing", "ja")
    assistant_prefs.get_preferences("fonts", "ar")
    assistant_prefs.change_preferences({"look.size_wide": "110"})
    assistant_prefs.reset_preferences("timing", "en")
    assistant_prefs.use_preset("calm")
    assistant_prefs.use_preset("mine", save_current=True)
    assert asked == [
        ("/prefs?lang=ar&group=", None), ("/prefs?lang=ja&group=timing", None),
        ("/prefs/fonts?lang=ar", None),
        ("/prefs", {"values": {"look.size_wide": "110"}, "language": "ar"}),
        ("/prefs/reset", {"what": "timing", "language": "en"}),
        ("/prefs/preset", {"name": "calm"}), ("/prefs/preset", {"save_as": "mine"})]


def test_a_translation_takes_settings_for_that_video_only(asked: list[tuple[str, Any]]) -> None:
    assistant.translate_video("C:\\v.mp4", "ar-msa", {"result": "subtitles",
                                                      "tweaks": {"text.reading_cps": 15}})
    assistant.translate_video("C:\\v.mp4", "en", "burned")
    assistant.translate_video("C:\\v.mp4", "en", {"tweaks": "bigger"})
    assert asked[0] == ("/jobs/local", {"path": "C:\\v.mp4", "target": "ar", "mode": "srt",
                                        "dialect": "msa", "tweaks": {"text.reading_cps": 15}})
    assert "tweaks" not in asked[1][1] and asked[1][1]["mode"] == "burn"
    assert asked[2][1]["tweaks"] == {"tweaks": "bigger"} and asked[2][1]["mode"] == "burn"


def test_a_chat_changes_settings_and_hears_why_one_is_refused(live: int,
                                                              prefs_home: Path) -> None:
    out = assistant_prefs.change_preferences({"look.size_wide": 300, "look.bold": "no"})
    assert out["saved"] == ["look.bold"] and "120" in out["refused"]["look.size_wide"]
    look = assistant_prefs.get_preferences("look")
    assert look["values"]["look.bold"] is False and look["changed"] == ["look.bold"]
    assert {s["group"] for s in look["specs"]} == {"look"}
    used = assistant_prefs.use_preset("bold")  # with the person's own bold off: their mix
    assert (used["used"], used["preset"]) == ("bold", "")
    assert assistant_prefs.use_preset("nothing-like-it")["error"] == 404
    assert "look.bold" in assistant_prefs.reset_preferences("all")["reset"]
    assert assistant_prefs.get_preferences()["changed"] == []
    assert (prefs_home / "preferences.json").is_file()


def test_a_chat_order_with_a_setting_that_breaks_is_refused_with_its_reason(
        live: int, tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"video")
    out = assistant.translate_video(str(clip), "ar", {"tweaks": {"look.size_wide": 300}})
    assert out["error"] == 400 and "look.size_wide" in out["detail"]
    job = assistant.translate_video(str(clip), "ar", {"tweaks": {"look.size_wide": 110}})
    assert job["stage"] == "queued"
