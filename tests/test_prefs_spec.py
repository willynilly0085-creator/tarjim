"""Every setting passes one gate (2026-11-09): its default is taken for every language, a value
outside its range or off its step is refused with the value that would work, and nothing that
could break the subtitle file (a comma in a font name, a colour that is not one) gets through."""
from pathlib import Path

import pytest

from tarjim.languages import LANGUAGES
from tarjim.prefs.spec import Refusal, Spec, check
from tarjim.prefs.table import GROUPS, SPECS, in_group

CODES = [*LANGUAGES, "xx"]


def refused(spec: Spec, raw: object) -> Refusal:
    found = check(spec, raw)
    assert isinstance(found, Refusal), (spec.key, raw, found)
    assert found.key == spec.key and f"«{spec.label}»" in found.reason
    return found


@pytest.mark.parametrize("key", sorted(SPECS))
def test_every_default_is_taken_for_every_language(key: str, prefs_home: Path) -> None:
    for code in CODES:
        spec = SPECS[key].at(code)
        assert check(spec, spec.default) == spec.default, (key, code)


NUMBERS = sorted(k for k, s in SPECS.items() if s.kind == "number")


@pytest.mark.parametrize("key", NUMBERS)
def test_every_range_holds_at_both_ends_for_every_language(key: str) -> None:
    for code in CODES:
        spec = SPECS[key].at(code)
        assert spec.low <= float(spec.default) <= spec.high, (key, code)
        assert check(spec, spec.low) == pytest.approx(spec.low)
        assert check(spec, spec.high) == pytest.approx(spec.high)
        below = refused(spec, spec.low - max(spec.step, 0.01))
        above = refused(spec, spec.high + max(spec.step, 0.01))
        assert below.works == pytest.approx(spec.low) and above.works == pytest.approx(spec.high)


@pytest.mark.parametrize("key", [k for k in NUMBERS if SPECS[k].step])
def test_a_value_off_the_step_names_the_nearest_step(key: str) -> None:
    spec = SPECS[key]
    off = spec.low + spec.step * 1.4
    if off > spec.high:
        return
    assert refused(spec, off).works == pytest.approx(spec.low + spec.step)


def test_numbers_are_read_as_people_write_them() -> None:
    spec = SPECS["look.box_opacity"]
    assert check(spec, "80%") == 80 and check(spec, "٨٠") == 80 and check(spec, 80.0) == 80
    assert isinstance(check(spec, 80.0), int)
    for bad in ("soon", "nan", "inf", True, "", None, [80], {"v": 80}):
        refused(spec, bad)
    assert check(SPECS["timing.linger"], "0٫6") == 0.6


def test_per_language_ranges_follow_the_script() -> None:
    cps = SPECS["text.reading_cps"]
    assert (cps.at("ar").low, cps.at("ar").high, cps.at("ar").default) == (12, 22, 17)
    assert (cps.at("ja").low, cps.at("ja").high, cps.at("ja").default) == (3, 6, 4)
    assert (cps.at("zh").low, cps.at("zh").high) == (6, 12)
    assert (cps.at("ko").low, cps.at("ko").high) == (6, 12)
    assert refused(cps.at("ja"), 13).works == 6
    chars = SPECS["text.line_chars"]
    assert (chars.at("ar").low, chars.at("ar").high, chars.at("th").default) == (32, 50, 35)
    assert (chars.at("zh").low, chars.at("zh").high, chars.at("ja").default) == (12, 20, 13)
    assert SPECS["look.font"].at("ar").default == "Dubai"
    assert SPECS["look.font"].at("ja").default == "Yu Gothic UI"


@pytest.mark.parametrize("key", sorted(k for k, s in SPECS.items() if s.kind == "choice"))
def test_every_choice_is_taken_and_nothing_else(key: str) -> None:
    spec = SPECS[key]
    assert spec.default == spec.choices[0]
    for option in spec.choices:
        assert check(spec, option) == option and check(spec, str(option)) == option
    assert refused(spec, "something else").works == spec.default


def test_choices_that_are_numbers_are_matched_as_numbers() -> None:
    assert check(SPECS["listen.passes"], "5") == 5
    refused(SPECS["listen.passes"], 2)  # an even count has no majority
    assert check(SPECS["timing.scene_sensitivity"], "0.50") == 0.5
    assert check(SPECS["look.dialogue_dash"], "—") == "— "
    refused(SPECS["look.dialogue_dash"], "")


def test_switches_take_the_usual_words() -> None:
    spec = SPECS["look.mark"]
    for yes in (True, "on", "yes", "1", "نعم", "شغال"):
        assert check(spec, yes) is True
    for no in (False, "off", "no", "0", "لا", "طافي"):
        assert check(spec, no) is False
    refused(spec, "maybe")


def test_colours_are_cleaned_and_anything_else_refused() -> None:
    spec = SPECS["look.text_colour"]
    assert check(spec, "#ffcc00") == "#FFCC00" and check(spec, "fc0") == "#FFCC00"
    for bad in ("red", "#12345", "#GGGGGG", "&H00FFFFFF", 0xFFFFFF):
        refused(spec, bad)
    palette = SPECS["look.speaker_palette"]
    assert check(palette, "#ffe066, 8fe3f5،#A8E6A1") == "#FFE066,#8FE3F5,#A8E6A1"
    refused(palette, "")
    refused(palette, ",".join(["#FFFFFF"] * 7))
    refused(palette, "#FFFFFF,blue")


def test_a_font_name_cannot_break_the_subtitle_file() -> None:
    spec = SPECS["look.font"]
    assert check(spec, "  Noto Naskh Arabic ") == "Noto Naskh Arabic"
    assert check(spec, "خط دبي") == "خط دبي"
    for bad in ("Dubai,Bold", "Dubai\nStyle: X", "{\\b1}", "", "a" * 65, "_hidden"):
        refused(spec, bad)


def test_the_folder_must_be_a_real_folder_of_its_own(tmp_path: Path,
                                                     prefs_home: Path) -> None:
    spec = SPECS["output.folder"]
    mine = tmp_path / "videos"
    mine.mkdir()
    assert check(spec, str(mine)) == str(mine.resolve())
    prefs_home.mkdir()
    for bad in (str(tmp_path / "missing"), "videos", "\\\\server\\share\\x", str(Path.home()),
                str(Path.home() / "Downloads"), Path(tmp_path.anchor).as_posix(),
                str(prefs_home), str(prefs_home / "cache"), ""):
        assert refused(spec, bad).works == spec.default, bad


def test_system_folders_and_ones_we_cannot_write_in_are_refused(
        tmp_path: Path, prefs_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09: on Windows os.access only reads the read-only flag, so the gate writes a
    file to find out, and the system's own folders are refused before that."""
    from tarjim.prefs import folders

    spec = SPECS["output.folder"]
    system, programs, mine = tmp_path / "Windows", tmp_path / "Programs", tmp_path / "mine"
    for place in (system / "System32", programs / "App", mine):
        place.mkdir(parents=True)
    monkeypatch.setenv("WINDIR", str(system))
    monkeypatch.setenv("ProgramFiles", str(programs))
    for bad in (system, system / "System32", programs, programs / "App"):
        assert refused(spec, str(bad)).works == spec.default, bad
    assert check(spec, str(mine)) == str(mine.resolve())
    assert list(mine.iterdir()) == []  # the trial file is gone
    monkeypatch.setattr(folders, "writable", lambda _place: False)
    assert "نكتب" in refused(spec, str(mine)).reason


def test_every_setting_belongs_to_a_page_tab_and_says_who_may_change_it() -> None:
    assert {s.group for s in SPECS.values()} == set(GROUPS)
    assert sum(len(in_group(g)) for g in GROUPS) == len(SPECS)
    assert {s.tier for s in SPECS.values()} == {"basic", "advanced"}
    assert not SPECS["output.folder"].per_job and SPECS["look.size_wide"].per_job
    assert all(s.label and "." in s.key for s in SPECS.values())


def test_settings_that_only_lower_accuracy_are_not_offered() -> None:
    gone = {"listen.sync_retry", "listen.speaker_sensitivity", "listen.relisten_gaps",
            "listen.fill_from_local", "listen.always_fresh", "dub.max_speedup",
            "output.audio_bitrate", "output.keep_srt", "translate.keep_tone",
            "translate.sounds", "timing.max_source_chars", "text.min_budget",
            "text.clause_break", "listen.engine", "listen.gemini_model",
            "listen.openai_model", "dub.eleven_model", "translate.glossary",
            "translate.target", "translate.mode", "translate.dialect", "output.name_dialect"}
    assert not gone & set(SPECS)
