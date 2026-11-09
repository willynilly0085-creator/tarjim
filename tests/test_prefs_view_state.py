"""What GET /prefs tells the page beyond one language's values (2026-11-09): whether a number is
whole, so a slider never rounds 17.5 letters a second to 18; and everything "رجّع كل شي للأصلي"
would put back, in every language, so the page neither says nothing changed nor asks about one
setting and then puts back three."""
from pathlib import Path

import pytest

from tarjim.prefs.edit import reset
from tarjim.prefs.view import save, state


def test_a_number_says_whether_it_is_whole() -> None:
    specs = {spec["key"]: spec for spec in state("ar")["specs"]}
    assert specs["look.size_wide"]["whole"] is True
    assert specs["text.line_chars"]["whole"] is True
    # 17.0, 1.0 and 2.0 reach the page's script as 17, 1 and 2: the default cannot tell it
    for key in ("text.reading_cps", "timing.max_duration", "timing.join_gap",
                "timing.cut_dialogue_span", "listen.gap_seconds"):
        assert specs[key]["whole"] is False, key
    assert specs["look.bold"]["whole"] is False  # a switch is not a number


@pytest.mark.usefixtures("prefs_home")
def test_everything_counts_what_every_language_would_put_back() -> None:
    assert save({"text.reading_cps": 15, "text.line_chars": 38}, "en")["refused"] == {}
    seen = state("ar")
    assert seen["changed"] == [] and set(seen["changed_all"]) == {"text.reading_cps",
                                                                  "text.line_chars"}
    assert seen["others"] is True  # English's own values go back too
    save({"look.bold": False}, "ar")
    seen = state("ar", "look")  # one tab asked for: everything still counts everything
    assert seen["changed"] == ["look.bold"]
    assert sorted(seen["changed_all"]) == sorted(reset("all", ""))
    after = state("ar")
    assert after["changed_all"] == [] and after["others"] is False


@pytest.mark.usefixtures("prefs_home")
def test_only_this_language_changed_puts_back_nothing_elsewhere(prefs_home: Path) -> None:
    save({"text.reading_cps": 15, "look.bold": False}, "ar")
    seen = state("ar")
    assert sorted(seen["changed_all"]) == sorted(seen["changed"])
    assert seen["others"] is False
    assert state("en")["others"] is True  # from English, Arabic's reading speed is elsewhere
    assert prefs_home.joinpath("preferences.json").is_file()
