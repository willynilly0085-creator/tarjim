"""The settings page's routes (2026-11-09): every setting is read with its range, saved through
the one gate, refused with an Arabic reason, reset, and grouped into presets."""
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from prefs_server import ask, serving

from tarjim.prefs.table import SPECS
from tarjim.render import font_cover
from tarjim.server.jobs import Board


@pytest.fixture
def port(prefs_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    monkeypatch.setattr(font_cover, "covering", lambda _code: ["Dubai", "Arial"])
    with serving(Board(lambda _task: None), tmp_path / "uploads") as found:
        yield found


def saved_file(home: Path) -> dict[str, object]:
    data = json.loads((home / "preferences.json").read_text(encoding="utf-8"))
    return dict(data["values"])


def test_the_page_reads_every_setting_with_its_range_and_value(port: int) -> None:
    code, state = ask(port, "GET /prefs")
    assert code == 200 and len(state["specs"]) == len(SPECS) == len(state["values"])
    size = next(s for s in state["specs"] if s["key"] == "look.size_wide")
    assert (size["low"], size["high"], size["step"], size["tier"]) == (80, 120, 5, "basic")
    assert state["values"]["look.style"] == "box" and state["changed"] == []
    assert state["preset"] == "original" and "calm" in state["presets"]["built_in"]
    code, timing = ask(port, "GET /prefs?group=timing&lang=ja")
    assert {s["group"] for s in timing["specs"]} == {"timing"} and timing["language"] == "ja"
    reading = ask(port, "GET /prefs?lang=ja&group=text")[1]["values"]["text.reading_cps"]
    assert reading == 4.0
    assert ask(port, "GET /prefs?lang=xx") == (400, {"error": "language"})
    assert ask(port, "GET /prefs?group=evil") == (400, {"error": "group"})


def test_a_save_keeps_what_passes_and_refuses_the_rest_with_its_reason(
        port: int, prefs_home: Path) -> None:
    wanted = {"look.size_wide": 110, "look.box_opacity": 30, "look.nope": 1}
    code, out = ask(port, "POST /prefs", {"values": wanted, "language": "ar"})
    assert code == 200 and out["saved"] == ["look.size_wide"]
    assert "60" in out["refused"]["look.box_opacity"] and "«قوة الخلفية»" in out["refused"][
        "look.box_opacity"]
    assert "look.nope" in out["refused"]["look.nope"]
    assert saved_file(prefs_home) == {"look.size_wide": 110}
    state = ask(port, "GET /prefs")[1]
    assert state["changed"] == ["look.size_wide"] and state["values"]["look.size_wide"] == 110
    assert ask(port, "POST /prefs", {"values": []})[0] == 400
    assert ask(port, "POST /prefs", {"values": {"look.bold": False}, "language": "xx"}) == (
        400, {"error": "language"})


def test_a_change_that_breaks_a_rule_between_settings_is_refused(port: int) -> None:
    out = ask(port, "POST /prefs", {"values": {"timing.min_gap": 0.25,
                                               "look.text_colour": "#151413"}})[1]
    assert out["saved"] == [] and set(out["refused"]) == {"timing.min_gap", "look.text_colour"}
    assert "القيمة اللي تنفع: 0.2" in out["refused"]["timing.min_gap"]
    assert ask(port, "GET /prefs")[1]["changed"] == []


def test_a_setting_kept_per_language_says_which_language_it_was_saved_for(port: int) -> None:
    out = ask(port, "POST /prefs", {"values": {"text.reading_cps": 15}, "language": "ar"})[1]
    assert out["saved"] == ["text.reading_cps"] and "العربية" in out["notes"][0]
    assert ask(port, "GET /prefs?lang=ar")[1]["values"]["text.reading_cps"] == 15
    assert ask(port, "GET /prefs?lang=en")[1]["values"]["text.reading_cps"] == 17


def test_a_setting_that_does_nothing_with_the_others_says_why(port: int) -> None:
    ask(port, "POST /prefs", {"values": {"look.style": "outline"}})
    state = ask(port, "GET /prefs?group=look")[1]
    assert "«على خلفية»" in state["idle"]["look.box_opacity"]
    assert "look.outline_width" not in state["idle"]
    out = ask(port, "POST /prefs", {"values": {"look.box_opacity": 80}})[1]
    assert out["saved"] == ["look.box_opacity"] and "«على خلفية»" in out["notes"][0]


def test_a_font_this_computer_cannot_write_the_language_in_is_refused(
        port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    out = ask(port, "POST /prefs", {"values": {"look.font": "Comic Sans MS"}})[1]
    assert out["saved"] == [] and "Arial" in out["refused"]["look.font"]
    assert ask(port, "POST /prefs", {"values": {"look.font": "Arial"}})[1]["saved"] == [
        "look.font"]
    assert ask(port, "GET /prefs/fonts?lang=ar") == (200, {
        "language": "ar", "usual": "Dubai", "fonts": ["Dubai", "Arial"], "listed": True})
    assert ask(port, "GET /prefs/fonts?lang=xx")[0] == 400
    monkeypatch.setattr(font_cover, "covering", lambda _code: None)
    assert ask(port, "GET /prefs/fonts?lang=ja")[1]["listed"] is False
    assert ask(port, "POST /prefs", {"values": {"look.font": "Anything"}})[1]["saved"]


def test_settings_go_back_to_the_original_by_key_group_or_all(port: int,
                                                              prefs_home: Path) -> None:
    ask(port, "POST /prefs", {"values": {"look.size_wide": 110, "look.bold": False,
                                         "timing.linger": 0.6, "dub.balance": 50}})
    assert ask(port, "POST /prefs/reset", {"keys": ["look.size_wide"]})[1]["reset"] == [
        "look.size_wide"]
    assert ask(port, "POST /prefs/reset", {"group": "timing"})[1]["reset"] == ["timing.linger"]
    assert ask(port, "POST /prefs/reset", {"what": "look"})[1]["reset"] == ["look.bold"]
    code, out = ask(port, "POST /prefs/reset", {"all": True})
    assert (code, out) == (200, {"reset": ["dub.balance"], "preset": "original"})
    assert saved_file(prefs_home) == {}
    for wrong in ({"keys": ["evil"]}, {"keys": []}, {}, {"group": "evil"}):
        assert ask(port, "POST /prefs/reset", wrong) == (400, {"error": "what"})
    assert ask(port, "POST /prefs/reset", {"all": True, "language": "xx"})[0] == 400


def test_presets_are_used_kept_renamed_and_deleted(port: int) -> None:
    code, out = ask(port, "POST /prefs/preset", {"name": "calm"})
    assert (code, out) == (200, {"used": "calm", "preset": "calm"})
    assert "look.fade_ms" in ask(port, "GET /prefs")[1]["changed"]
    code, out = ask(port, "POST /prefs/preset", {"name": "nope"})
    assert code == 404 and out["error"] == "ما فيه مجموعة بهالاسم."
    assert ask(port, "POST /prefs/preset", {"save_as": "mine"}) == (
        200, {"saved": "mine", "preset": "calm"})
    assert ask(port, "GET /prefs")[1]["presets"]["own"] == ["mine"]
    code, out = ask(port, "POST /prefs/preset", {"save_as": "calm"})
    assert code == 400 and "اسم ثاني" in out["error"]
    assert ask(port, "POST /prefs/preset", {"rename": "mine", "to": "ours"})[0] == 200
    assert ask(port, "POST /prefs/preset", {"delete": "ours"})[0] == 200
    assert ask(port, "POST /prefs/preset", {"delete": "ours"})[0] == 404
    assert ask(port, "POST /prefs/preset", {})[0] == 400
