"""A chosen font draws the subtitles only when it is on this computer (2026-11-09)."""
from pathlib import Path

import pytest

from tarjim.job import Job
from tarjim.prefs.active import using
from tarjim.prefs.model import resolve
from tarjim.render import fonts
from tests.test_mark import outputs

INSTALLED = ["Dubai Bold (TrueType)", "Cambria & Cambria Math (TrueType)", "Segoe UI (TrueType)",
             "Amiri Quran (OpenType)"]


@pytest.fixture
def listed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fonts, "installed", lambda: frozenset(fonts.names_in(INSTALLED)))


def test_the_families_are_read_from_the_registrys_names() -> None:
    assert fonts.names_in(INSTALLED) == {"dubai bold", "cambria", "cambria math", "segoe ui",
                                         "amiri quran"}


@pytest.mark.usefixtures("listed")
def test_a_font_that_is_not_installed_gives_way_to_the_languages_own(
        capsys: pytest.CaptureFixture[str]) -> None:
    assert fonts.usable("Amiri", "Dubai") == "Amiri"
    assert fonts.usable("Cambria Math", "Dubai") == "Cambria Math"
    assert fonts.usable("Comic Sans MS", "Dubai") == "Dubai"
    assert "not on this computer" in capsys.readouterr().out
    assert fonts.usable("Dubai", "Dubai") == "Dubai"


def test_a_list_that_cannot_be_read_trusts_the_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fonts, "installed", lambda: None)
    assert fonts.usable("Anything", "Dubai") == "Anything"


@pytest.mark.usefixtures("listed")
def test_the_subtitle_file_names_the_chosen_font_or_the_usual_one(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for chosen, drawn in (("Segoe UI", "Segoe UI"), ("Comic Sans MS", "Dubai")):
        prefs = resolve({"look.font": chosen}, {}, "ar")
        job = Job(tmp_path / "v.mp4", out_dir=tmp_path, cache_dir=tmp_path / "c", prefs=prefs)
        with using(prefs):
            ass = outputs(tmp_path, monkeypatch, job)[0][1]
        assert f"Style: Default,{drawn},42," in ass  # tests.test_mark draws on 1280x720
