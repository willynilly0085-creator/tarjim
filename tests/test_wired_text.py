"""Each reading and timing setting reaches the rules that cut and time the subtitles, and
nothing else; with nothing changed the rules are the ones tarjim cut by before (2026-11-09)."""
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from tarjim import media, pipeline
from tarjim.job import Job
from tarjim.languages import LANGUAGES, language
from tarjim.lines import balance_lines
from tarjim.models import Cue, Word
from tarjim.prefs.active import using
from tarjim.prefs.model import resolve
from tarjim.qa import check
from tarjim.render.room import fitted
from tarjim.rules import Rules, rules_for
from tarjim.segment import build_cues

EXCHANGE = [Word("Did", 0.0, 0.3, "S1"), Word("you", 0.3, 0.6, "S1"), Word("go?", 0.6, 1.0, "S1"),
            Word("Yes,", 1.2, 1.5, "S2"), Word("twice.", 1.5, 1.9, "S2")]
PAUSED = [Word("Hello", 0, 0.5), Word("there", 0.5, 1.0), Word("General", 2.6, 3.1),
          Word("Kenobi", 3.1, 3.6)]


def rules(values: dict[str, Any], code: str = "ar") -> Rules:
    return rules_for(language(code), resolve(values, {}, code))


def differences(values: dict[str, Any]) -> dict[str, Any]:
    usual, chosen = rules({}), rules(values)
    return {f.name: getattr(chosen, f.name) for f in fields(Rules)
            if getattr(chosen, f.name) != getattr(usual, f.name)}


def test_nothing_changed_cuts_by_the_rules_of_before() -> None:
    for code in LANGUAGES:
        assert rules({}, code) == rules_for(language(code)), code


@pytest.mark.parametrize(("values", "expected"), [
    ({"text.reading_cps": 20.0}, {"reading_cps": 20.0}),
    ({"text.line_chars": 36}, {"line_chars": 36, "max_source_chars": 72}),
    ({"text.reading_warning": 1.5}, {"warn_at": 1.5}),
    ({"timing.min_duration": 0.6}, {"min_duration": 0.6}),
    ({"timing.max_duration": 7.0}, {"max_duration": 7.0}),
    ({"timing.linger": 0.8}, {"linger": 0.8}),
    ({"timing.min_gap": 0.15}, {"min_gap": 0.15}),
    ({"timing.long_pause": 1.2}, {"long_pause": 1.2}),
    ({"timing.join_gap": 0.5}, {"join_gap": 0.5}),
    ({"timing.min_readable": 1.2}, {"min_readable": 1.2}),
    ({"timing.cut_snap": 0.1}, {"cut_snap": 0.1}),
    ({"timing.cut_dialogue_span": 0.0}, {"cut_dialogue_span": 0.0}),
    ({"timing.dialogue_cues": False}, {"max_speakers": 1}),
    ({"timing.dialogue_cues": False, "text.one_line": True},
     {"max_speakers": 1, "max_lines": 1, "max_source_chars": 42}),
    ({"look.dialogue_dash": "– "}, {"dash": "– "}),
    ({"look.staged_reveal": False}, {"staged": False}),
])
def test_each_setting_changes_its_own_rule(values: dict[str, Any],
                                           expected: dict[str, Any]) -> None:
    assert differences(values) == expected


def test_one_line_keeps_a_long_translation_on_one_line() -> None:
    text = "هذا سطر طويل شوي فيه كلام كثير يكفي يتقسم على سطرين عادة"
    assert len(balance_lines(text, rules({}))) == 2
    one = rules({"timing.dialogue_cues": False, "text.one_line": True})
    assert balance_lines(text, one) == [text]


def test_a_shorter_pause_starts_a_new_subtitle_and_lingering_holds_it() -> None:
    assert len(build_cues(PAUSED, [], rules({}))) == 1
    assert len(build_cues(PAUSED, [], rules({"timing.long_pause": 1.2}))) == 2
    usual, longer = (build_cues(PAUSED, [], rules(v))[-1].end
                     for v in ({}, {"timing.linger": 0.8}))
    assert longer == pytest.approx(usual + 0.4)


def test_without_dialogue_cues_each_speaker_has_a_subtitle_of_their_own() -> None:
    assert [len(c.parts) for c in build_cues(EXCHANGE, [], rules({}))] == [2]
    alone = build_cues(EXCHANGE, [], rules({"timing.dialogue_cues": False}))
    assert [len(c.parts) for c in alone] == [1, 1]


def test_the_report_warns_at_the_persons_reading_speed() -> None:
    fast = [Cue(0.0, 1.0, text="ا" * 22)]  # 22 letters a second, 1.3 times 17
    assert [i.kind for i in check(fast, rules({}))] == ["reading_speed"]
    assert check(fast, rules({"text.reading_warning": 1.5})) == []


def test_a_bigger_tall_size_fits_fewer_letters_on_a_standing_picture() -> None:
    usual, bigger = (fitted(rules({}), 1080, 1920, resolve(v, {}, "ar").look)
                     for v in ({}, {"look.size_tall": 120}))
    assert bigger.line_chars < usual.line_chars < 42
    assert fitted(rules({}), 1920, 1080, resolve({"look.size_tall": 120}, {}, "ar").look) == \
        rules({})


def scenes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
           values: dict[str, Any]) -> tuple[list[float], list[float]]:
    asked: list[float] = []

    def scan(_video: Path, threshold: float = media.SCENE_THRESHOLD) -> list[float]:
        asked.append(threshold)
        return [1.0, 2.0]

    monkeypatch.setattr(media, "scene_cuts", scan)
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path / "cache")
    with using(resolve(values, {}, "ar")):
        return pipeline.cuts_for(job), asked


def test_scene_cuts_follow_the_sensitivity_and_can_be_left_out(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "v.mp4").write_bytes(b"x")
    assert scenes(tmp_path, monkeypatch, {}) == ([1.0, 2.0], [0.25])
    assert (tmp_path / "cache" / "v" / "cuts.json").is_file()
    assert scenes(tmp_path, monkeypatch, {"timing.scene_sensitivity": 0.5}) == ([1.0, 2.0], [0.5])
    assert (tmp_path / "cache" / "v" / "cuts-0.5.json").is_file()
    assert scenes(tmp_path, monkeypatch, {"timing.end_at_cuts": False}) == ([], [])
