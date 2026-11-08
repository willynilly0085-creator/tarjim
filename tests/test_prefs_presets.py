"""Ready sets of settings (2026-11-09): each passes the gate and every rule in every language;
it puts back and sets only the settings it names, never the mark or the font; a setting kept
per language is a share of each language's own default; the person may keep ten of their own."""
import json
from pathlib import Path

import pytest

from tarjim.languages import LANGUAGES
from tarjim.prefs.edit import change, delete_preset, rename_preset, save_preset, use_preset
from tarjim.prefs.model import resolve
from tarjim.prefs.presets import BUILT_IN, MOST_OWN, ORIGINAL, OUTSIDE, Share, active, applied
from tarjim.prefs.spec import Refusal, check
from tarjim.prefs.store import current, load
from tarjim.prefs.table import SPECS


@pytest.mark.parametrize("name", sorted(BUILT_IN))
def test_every_preset_is_taken_whole_in_every_language(name: str) -> None:
    preset = BUILT_IN[name]
    assert not OUTSIDE & set(preset) and set(preset) <= set(SPECS)
    stored = applied({}, preset)
    for code in LANGUAGES:
        prefs = resolve(stored, {}, code)
        assert prefs.notes == (), (name, code)
        for key, value in preset.items():
            if not isinstance(value, Share):
                assert prefs.values[key] == value and check(SPECS[key], value) == value
    assert active(stored, {}) == name


def test_a_share_follows_each_language_and_stays_in_its_range() -> None:
    stored = applied({}, BUILT_IN["verbatim"])
    speeds = {code: resolve(stored, {}, code).text.reading_cps for code in ("ar", "ja", "ko")}
    assert speeds == {"ar": 20.5, "ja": 5.0, "ko": 12.0}  # Korean is at its fastest already
    assert "ko" not in stored["text.reading_cps"]  # unchanged from its default: not written
    lines = applied({}, BUILT_IN["phone"])["text.line_chars"]
    assert lines["ar"] == 34 and lines["ja"] == 12 and lines["th"] == 32


def test_a_preset_resets_only_what_it_names(prefs_home: Path) -> None:
    change({"look.font": "Tahoma", "look.mark": False, "look.text_colour": "#FFFFFF",
            "look.size_wide": 90, "timing.linger": 0.2, "look.bold": False})
    assert use_preset("calm")
    prefs = current()
    assert prefs.look.font == "Tahoma" and prefs.look.mark is False
    assert prefs.look.text_colour == "#FFFFFF"  # calm does not name the colour
    assert prefs.look.size_wide == 95 and prefs.timing.linger == 0.6
    assert active(load().values, {}) == ""  # calm and the person's own changes
    assert use_preset(ORIGINAL)
    assert load().values == {"look.font": {"ar": "Tahoma"}, "look.mark": False}
    assert active(load().values, {}) == ORIGINAL
    assert not use_preset("nothing")


def test_a_bigger_font_makes_room_by_shortening_the_line(prefs_home: Path) -> None:
    assert change({"text.line_chars": 50}).saved == ["text.line_chars"]
    assert use_preset("bold")
    prefs = current()
    assert prefs.look.size_wide == 115 and prefs.look.style == "outline"
    assert 42 <= prefs.text.line_chars < 50 and prefs.notes == ()


def test_the_person_keeps_presets_of_their_own(prefs_home: Path) -> None:
    change({"look.size_wide": 110, "look.mark": False, "timing.linger": 0.6})
    assert save_preset("  مسلسلات ") == ""
    assert load().presets == {"مسلسلات": {"look.size_wide": 110, "timing.linger": 0.6}}
    assert active(load().values, load().presets) == "مسلسلات"  # the mark is outside presets
    use_preset(ORIGINAL)
    assert use_preset("مسلسلات") and current().look.size_wide == 110
    assert current().look.mark is False
    assert save_preset("calm") and save_preset("") and save_preset("x" * 41)
    assert rename_preset("مسلسلات", "أفلام") == "" and "أفلام" in load().presets
    assert rename_preset("nothing", "y") and rename_preset("أفلام", "news")
    assert delete_preset("أفلام") and not delete_preset("أفلام")


def test_no_more_than_ten_of_their_own(prefs_home: Path) -> None:
    for number in range(MOST_OWN):
        assert save_preset(f"set {number}") == ""
    assert "10" in save_preset("one more")
    assert save_preset("set 3") == ""  # saving over one of them is fine


def test_a_hand_edited_preset_cannot_slip_a_bad_value_in(prefs_home: Path) -> None:
    prefs_home.mkdir()
    data = {"version": 1, "values": {},
            "presets": {"mine": {"look.size_wide": 999, "look.bold": False}, "bad": 3}}
    (prefs_home / "preferences.json").write_text(json.dumps(data), encoding="utf-8")
    assert list(load().presets) == ["mine"]
    assert use_preset("mine")
    prefs = current()
    assert prefs.look.size_wide == 100 and prefs.look.bold is False and prefs.notes
    assert isinstance(check(SPECS["look.size_wide"], 999), Refusal)
