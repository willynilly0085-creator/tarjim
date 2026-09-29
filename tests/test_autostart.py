from pathlib import Path

import pytest

from tarjim import autostart


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(autostart.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
    return tmp_path


@pytest.mark.parametrize("system", ["win32", "darwin", "linux"])
def test_starting_with_the_computer_can_be_turned_on_and_off(
        home: Path, system: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autostart.sys, "platform", system)
    assert not autostart.enabled()
    autostart.enable()
    entry = autostart.entry()
    assert autostart.enabled() and entry.is_file()
    assert "tarjim.server" in entry.read_text(encoding="utf-8")
    autostart.disable()
    assert not autostart.enabled() and not entry.exists()


def test_windows_starts_the_engine_without_a_window(home: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    autostart.enable()
    script = autostart.entry().read_text(encoding="utf-8")
    assert "pythonw" in script.lower() and ", 0, False" in script
