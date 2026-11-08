"""The saved settings (2026-11-09): only what differs from a default is written; a reset
forgets it; config.json's old settings are copied once; their old names still work from the
environment; a hand-edited file that cannot be read leaves the defaults and a note."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config
from tarjim.prefs import store
from tarjim.prefs.edit import change, reset
from tarjim.prefs.job import from_snapshot, snapshot, vetted
from tarjim.prefs.model import resolve
from tarjim.prefs.store import current, load


def on_disk(home: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((home / "preferences.json").read_text(encoding="utf-8"))
    return data


def test_nothing_is_written_until_something_changes(prefs_home: Path) -> None:
    prefs = current()
    assert prefs.look.style == "box" and prefs.look.font == "Dubai" and prefs.notes == ()
    assert current("ja").text.reading_cps == 4.0 and current("ja").look.font == "Yu Gothic UI"
    assert not (prefs_home / "preferences.json").exists()


def test_only_what_differs_from_a_default_is_kept(prefs_home: Path) -> None:
    outcome = change({"look.size_wide": "110", "look.bold": "on", "text.line_chars": 40})
    assert outcome.saved == ["look.size_wide", "look.bold", "text.line_chars"]
    assert outcome.refused == {}
    assert on_disk(prefs_home) == {"version": 1, "presets": {},
                                   "values": {"look.size_wide": 110,
                                              "text.line_chars": {"ar": 40}}}
    change({"text.line_chars": 15}, language="zh")
    assert on_disk(prefs_home)["values"]["text.line_chars"] == {"ar": 40, "zh": 15}
    assert current("ar").text.line_chars == 40 and current("zh").text.line_chars == 15
    assert current("en").text.line_chars == 42
    change({"look.size_wide": 100})
    assert "look.size_wide" not in on_disk(prefs_home)["values"]


def test_a_refused_change_keeps_nothing_of_itself(prefs_home: Path) -> None:
    outcome = change({"look.box_opacity": 30, "look.mark": "off", "look.nothing": 1,
                      "timing.min_readable": 0.6})
    assert outcome.saved == ["look.mark"]
    assert set(outcome.refused) == {"look.box_opacity", "look.nothing", "timing.min_readable"}
    assert "60" in outcome.refused["look.box_opacity"]
    assert on_disk(prefs_home)["values"] == {"look.mark": False}
    assert change({"look.box_opacity": 10}).saved == []


def test_a_shared_change_must_hold_for_every_language_s_own_values(prefs_home: Path) -> None:
    """2026-11-09: a bigger font that French's own longer line no longer fits is refused,
    naming French, instead of saved and then quietly undone when a French job reads it."""
    assert change({"text.line_chars": 50}, "fr").saved == ["text.line_chars"]
    outcome = change({"look.size_wide": 120})
    assert outcome.saved == [] and "Français" in outcome.refused["look.size_wide"]
    assert current("fr").text.line_chars == 50 and current("fr").notes == ()
    works = change({"look.size_wide": 120}).refused["look.size_wide"]
    smaller = int(works.split(":")[-1].strip(" ."))
    assert smaller < 120 and change({"look.size_wide": smaller}).saved == ["look.size_wide"]
    assert current("fr").notes == () and current("fr").look.size_wide == smaller


def test_reset_one_setting_one_language_a_group_or_everything(prefs_home: Path) -> None:
    change({"look.size_wide": 110, "look.bold": False, "timing.linger": 0.6})
    change({"text.line_chars": 40, "text.reading_cps": 15})
    change({"text.line_chars": 15}, language="zh")
    assert reset("look.bold") == ["look.bold"] and current().look.bold is True
    assert reset("text.line_chars", language="zh") == ["text.line_chars"]
    assert on_disk(prefs_home)["values"]["text.line_chars"] == {"ar": 40}
    assert sorted(reset("text")) == ["text.line_chars", "text.reading_cps"]
    assert reset("nothing.here") == [] and reset("text") == []
    assert sorted(reset("all")) == ["look.size_wide", "timing.linger"]
    assert on_disk(prefs_home)["values"] == {}


def test_config_json_settings_are_copied_once(prefs_home: Path, tmp_path: Path) -> None:
    folder = tmp_path / "out"
    folder.mkdir()
    prefs_home.mkdir()
    old = {"video_mark": "no", "listen_chunk_seconds": "90", "coverage_gap_seconds": "9",
           "downloads": str(folder), "openai_listen_model": "whisper-1", "ui_language": "ar"}
    config.write_settings(old)
    prefs = current()
    assert prefs.look.mark is False and prefs.listen.chunk_seconds == 90
    assert prefs.output.folder == str(folder.resolve())
    assert prefs.listen.gap_seconds == 2.0  # 9 s would hide missed speech: not taken
    assert any("coverage_gap_seconds" in line for line in store.SAID)
    change({"look.bold": False})
    assert on_disk(prefs_home)["values"] == {"look.mark": False, "listen.chunk_seconds": 90,
                                             "output.folder": str(folder.resolve()),
                                             "look.bold": False}
    config.save("video_mark", "yes")  # an older tarjim still writes its own key
    assert current().look.mark is False
    assert json.loads(config.CONFIG.read_text(encoding="utf-8"))["video_mark"] == "yes"


def test_the_old_names_still_work_from_the_environment(prefs_home: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    change({"listen.chunk_seconds": 60})
    monkeypatch.setenv("TARJIM_VIDEO_MARK", "no")
    monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "120")
    monkeypatch.setenv("TARJIM_COVERAGE_GAP_SECONDS", "1")
    prefs = current()
    assert prefs.look.mark is False and prefs.listen.chunk_seconds == 120
    assert prefs.listen.gap_seconds == 1.0
    monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "soon")
    assert current().listen.chunk_seconds == 60
    assert any("TARJIM_LISTEN_CHUNK_SECONDS" in line for line in store.SAID)
    assert on_disk(prefs_home)["values"] == {"listen.chunk_seconds": 60}


@pytest.mark.parametrize("text", ["{not json", "[1, 2]", '"text"', "\x00\x01"])
def test_a_hand_edited_file_that_cannot_be_read_leaves_the_defaults(
        prefs_home: Path, text: str, capsys: pytest.CaptureFixture[str]) -> None:
    prefs_home.mkdir()
    (prefs_home / "preferences.json").write_text(text, encoding="utf-8")
    assert current() == current("ar") and current().look.size_wide == 100
    assert "could not be read" in capsys.readouterr().out
    change({"look.bold": False})
    assert on_disk(prefs_home)["values"] == {"look.bold": False}
    assert (prefs_home / "preferences.broken.json").read_text(encoding="utf-8") == text


def test_hand_edited_values_that_cannot_be_taken_are_left_out_one_by_one(
        prefs_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prefs_home.mkdir()
    values = {"look.size_wide": 500, "look.font": "Evil,Font", "look.bold": False,
              "text.line_chars": {"ar": "many", "zh": 14}, "look.unknown": 1,
              "timing.min_readable": 0.5}
    (prefs_home / "preferences.json").write_text(json.dumps({"version": 1, "values": values}),
                                                 encoding="utf-8")
    prefs = current()
    assert prefs.look.size_wide == 100 and prefs.look.font == "Dubai"
    assert prefs.look.bold is False and prefs.text.line_chars == 42
    assert prefs.timing.min_readable == 0.9 and current("zh").text.line_chars == 14
    said = capsys.readouterr().out
    assert said.count("preferences:") == len(prefs.notes) == 5
    assert "look.unknown" in said and "min_readable" in said
    current()
    assert capsys.readouterr().out == ""  # each note once a run


def test_a_busy_file_stops_the_save_instead_of_losing_it(
        prefs_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    change({"look.bold": False})
    monkeypatch.setattr(config, "PAUSE", 0)
    real = Path.read_text

    def busy(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "preferences.json":
            raise PermissionError("in use")
        return real(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", busy)
        with pytest.raises(PermissionError):
            change({"look.size_wide": 110})
    assert load().values == {"look.bold": False}


def test_one_video_s_own_changes_are_checked_and_kept_with_the_order(
        prefs_home: Path) -> None:
    change({"look.size_wide": 110})
    tweaks = {"look.style": "outline", "text.reading_cps": 15, "output.folder": "D:/x",
              "look.box_opacity": 20, "look.nope": 1}
    refused = vetted(load().values, tweaks, "ar")
    assert set(refused) == {"output.folder", "look.box_opacity", "look.nope"}
    prefs = current("ar", {"look.style": "outline", "text.reading_cps": 15})
    assert prefs.look.style == "outline" and prefs.look.size_wide == 110
    kept = snapshot(prefs)
    assert kept == {"version": 1, "values": {"look.style": "outline", "look.size_wide": 110,
                                             "text.reading_cps": 15.0}}
    json.dumps(kept)
    change({"look.size_wide": 90})
    assert from_snapshot(json.loads(json.dumps(kept)), "ar") == prefs
    assert from_snapshot({"version": 9}, "ar") == resolve({}, {}, "ar")
    assert from_snapshot("garbage", "ar").look.size_wide == 100
