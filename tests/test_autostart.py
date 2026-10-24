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


def test_windows_tries_once_more_when_the_engine_is_gone(home: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    script = autostart.windows_script(r"C:\py\pythonw.exe")
    assert script.count('shell.Run engine, 0, False') == 2
    assert r'engine = """C:\py\pythonw.exe"" -P -m tarjim.server"' in script
    assert "WScript.Sleep 60000" in script and "Win32_Process" in script
    assert str(autostart.HOME / "server.log") in script and "{" not in script


def test_an_older_startup_script_for_this_python_is_brought_up_to_date(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setattr(autostart, "quiet_python", lambda: r"C:\py\pythonw.exe")
    entry = autostart.entry()
    entry.parent.mkdir(parents=True)
    entry.write_text(r'CreateObject("WScript.Shell").Run """C:\py\pythonw.exe"" -P -m '
                     'tarjim.server", 0, False\n', encoding="utf-8")
    autostart.refresh()
    assert entry.read_text(encoding="utf-8") == autostart.windows_script(r"C:\py\pythonw.exe")


def test_a_startup_script_for_another_python_is_left_alone(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setattr(autostart, "quiet_python", lambda: r"C:\copy\pythonw.exe")
    entry = autostart.entry()
    entry.parent.mkdir(parents=True)
    entry.write_text(autostart.windows_script(r"C:\py\pythonw.exe"), encoding="utf-8")
    autostart.refresh()
    assert entry.read_text(encoding="utf-8") == autostart.windows_script(r"C:\py\pythonw.exe")
