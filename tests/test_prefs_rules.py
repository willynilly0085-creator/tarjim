"""The rules between settings (2026-11-09): the defaults keep every one of them in every
language; a change that breaks one is refused with an Arabic reason and a value that works;
a saved file that breaks one falls back to the default, with a note, and never fails a job."""
from typing import Any

import pytest

from tarjim.languages import LANGUAGES
from tarjim.prefs.checks import RULES, WIDE_FRAME, broken, line_chars_for, widest_line
from tarjim.prefs.model import resolve
from tarjim.prefs.settle import changes
from tarjim.prefs.table import defaults
from tarjim.render.room import fitted
from tarjim.rules import rules_for


def start(target: str = "ar", **wanted: Any) -> dict[str, Any]:
    return {**defaults(target), **{k.replace("__", "."): v for k, v in wanted.items()}}


def refusal_of(wanted: dict[str, Any], target: str = "ar") -> dict[str, Any]:
    after, refused = changes(defaults(target), wanted, target)
    assert not broken(after, target)
    return {key: (r.works, r.reason) for key, r in refused.items()}


@pytest.mark.parametrize("code", [*LANGUAGES, "xx"])
def test_the_defaults_keep_every_rule(code: str) -> None:
    assert broken(defaults(code), code) == []
    assert resolve({}, {}, code).notes == ()


def test_short_speech_is_joined_until_a_line_is_shown_its_least() -> None:
    found = refusal_of({"timing.min_readable": 0.7})
    assert found["timing.min_readable"][0] == 0.8
    assert "أقل مدة يبقى فيها السطر" in found["timing.min_readable"][1]
    assert refusal_of({"timing.min_duration": 1.0})["timing.min_duration"][0] == 0.9
    assert refusal_of({"timing.min_duration": 1.0, "timing.min_readable": 1.0}) == {}


def test_a_pause_that_joins_speech_is_shorter_than_one_that_starts_a_line() -> None:
    found = refusal_of({"timing.join_gap": 2.0, "timing.long_pause": 1.5})
    assert list(found) == ["timing.long_pause"]  # the change asked for last gives way
    assert found["timing.long_pause"][0] == 2.1


def test_the_gap_between_lines_is_at_most_a_quarter_of_the_shortest_line() -> None:
    found = refusal_of({"timing.min_gap": 0.25})
    assert found["timing.min_gap"][0] == pytest.approx(0.2, abs=0.003)
    assert refusal_of({"timing.min_gap": 0.25, "timing.min_duration": 1.0,
                       "timing.min_readable": 1.0}) == {}


def test_letters_must_stand_out_from_the_box_over_a_white_picture() -> None:
    found = refusal_of({"look.box_opacity": 60})
    assert found["look.box_opacity"][0] == 69  # the speakers' colours need that much cover
    assert "تباين" in found["look.box_opacity"][1]
    assert refusal_of({"look.speaker_colours": False, "look.box_opacity": 63}) == {}
    assert refusal_of({"look.speaker_colours": False, "look.box_opacity": 60})[
        "look.box_opacity"][0] == 61
    dark = refusal_of({"look.text_colour": "#333333"})
    assert dark["look.text_colour"][0] == "#F7F5F0"
    assert "look.box_colour" in refusal_of({"look.box_colour": "#FFFFFF"})
    assert "look.speaker_palette" in refusal_of({"look.speaker_palette": "#FFE066,#777777"})


def test_outlined_letters_are_held_to_their_own_edge() -> None:
    assert refusal_of({"look.style": "outline", "look.box_opacity": 60}) == {}  # no box drawn
    back = changes(start(look__style="outline", look__box_opacity=60), {"look.style": "box"},
                   "ar")[1]
    assert back["look.style"].works == "outline"  # the box would be too thin to read on
    found = refusal_of({"look.style": "outline", "look.outline_colour": "#DDDDDD"})
    assert list(found) == ["look.outline_colour"] and found["look.outline_colour"][0]


def test_a_line_must_fit_the_wide_picture_at_the_chosen_size() -> None:
    assert widest_line(defaults("ar"), "ar", WIDE_FRAME) >= 42
    found = refusal_of({"look.size_wide": 120, "look.side_margin": 12})
    assert list(found) == ["look.side_margin"]
    works = found["look.side_margin"][0]
    assert works < 12 and not broken(start(look__size_wide=120, look__side_margin=works), "ar")
    assert "عرض الفيديو" in found["look.side_margin"][1]
    assert refusal_of({"text.line_chars": 50, "look.size_wide": 120})["look.size_wide"][0] < 120
    assert refusal_of({"look.size_wide": 120, "look.side_margin": 12}, "zh") == {}


def test_a_standing_video_gets_the_line_room_measures() -> None:
    """The saved line length is for a wide picture; a standing one is given what fits, the
    same count render/room.py cuts the cues to."""
    for code in ("ar", "en", "zh", "ja", "th"):
        values = defaults(code)
        for frame in ((1080, 1920), (1920, 1080), (720, 1280), (1440, 1080)):
            expected = fitted(rules_for(LANGUAGES[code]), *frame).line_chars
            assert line_chars_for(values, code, frame) == expected, (code, frame)


def test_one_line_needs_one_speaker_a_line() -> None:
    found = refusal_of({"text.one_line": True})
    assert found["text.one_line"][0] is False and "متكلمين" in found["text.one_line"][1]
    assert refusal_of({"timing.dialogue_cues": False, "text.one_line": True}) == {}


def test_a_saved_file_that_breaks_a_rule_falls_back_with_a_note() -> None:
    prefs = resolve({"timing.min_readable": 0.6, "look.box_opacity": 60,
                     "text.line_chars": {"ar": 50}, "look.size_wide": 120}, {}, "ar")
    assert prefs.timing.min_readable == 0.9 and prefs.look.box_opacity == 69
    assert prefs.text.line_chars == 42 and prefs.look.size_wide == 120
    assert len(prefs.notes) == 3 and all("back to" in n for n in prefs.notes)
    assert not broken(prefs.values, "ar")


def test_every_rule_names_settings_that_exist_and_says_why_in_arabic() -> None:
    names = set(defaults("ar"))
    for rule in RULES:
        assert set(rule.keys) <= names and rule.why and not rule.why.isascii()


def test_eastern_digits_are_for_arabic_only() -> None:
    assert resolve({"translate.numbers": "eastern"}, {}, "ar").translate.numbers == "eastern"
    persian = resolve({"translate.numbers": "eastern"}, {}, "fa")
    assert persian.translate.numbers == "latin" and persian.notes
