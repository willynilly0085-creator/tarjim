"""The tarjim shortcut runs tarjim.wake, and the plain link to the page that older installers left
on the desktop is replaced by it once; a link tarjim did not write is left alone."""
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tarjim import shortcut

OLD_LINK = "[InternetShortcut]\r\nURL=http://127.0.0.1:17653\r\nIconIndex=0\r\n"
PYTHON = r"C:\Users\O'Brien\.local\share\uv\tools\tarjim\Scripts\pythonw.exe"


def test_the_shortcut_runs_wake_with_the_engines_own_python_and_icon() -> None:
    text = shortcut.script([Path(r"C:\Desk top\tarjim.lnk")], PYTHON)
    assert "$link.TargetPath = 'C:\\Users\\O''Brien\\" in text
    assert "$link.Arguments = '-P -m tarjim.wake'" in text
    assert str(shortcut.ICON) in text and shortcut.ICON.is_file()
    assert "'C:\\Desk top\\tarjim.lnk'" in text


def test_only_the_link_older_installers_wrote_is_ours(tmp_path: Path) -> None:
    mine, other = tmp_path / "tarjim.url", tmp_path / "other.url"
    mine.write_text(OLD_LINK, encoding="ascii")
    other.write_text("[InternetShortcut]\r\nURL=https://example.com/\r\n", encoding="ascii")
    assert shortcut.ours(mine) and not shortcut.ours(other)
    assert not shortcut.ours(tmp_path / "missing.url")


@pytest.fixture
def powershell(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Writes the shortcuts the script names, as PowerShell would."""
    ran: list[Any] = []

    def run(command: list[str], **options: Any) -> None:
        ran.append(command)
        for place in (shortcut.desktop() / shortcut.NAME, shortcut.start_menu() / shortcut.NAME):
            place.write_bytes(b"L")

    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    monkeypatch.setattr(shortcut.subprocess, "run", run)
    return ran


def test_without_an_old_link_nothing_is_written(powershell: list[Any]) -> None:
    assert not shortcut.upgrade() and powershell == []


def test_the_old_link_is_replaced_by_both_shortcuts(powershell: list[Any]) -> None:
    shortcut.desktop().mkdir(parents=True)
    (shortcut.desktop() / shortcut.OLD).write_text(OLD_LINK, encoding="ascii")
    assert shortcut.upgrade() and len(powershell) == 1
    assert not (shortcut.desktop() / shortcut.OLD).exists()
    assert (shortcut.start_menu() / shortcut.NAME).is_file()


def test_the_old_link_stays_when_the_shortcut_could_not_be_written(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shortcut.sys, "platform", "win32")
    monkeypatch.setattr(shortcut.subprocess, "run", lambda command, **options: None)
    shortcut.desktop().mkdir(parents=True)
    (shortcut.desktop() / shortcut.OLD).write_text(OLD_LINK, encoding="ascii")
    assert not shortcut.upgrade()
    assert (shortcut.desktop() / shortcut.OLD).is_file()


def test_other_systems_get_no_shortcut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shortcut.sys, "platform", "linux")
    assert shortcut.make() == [] and not shortcut.upgrade()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcuts")
def test_windows_writes_a_shortcut_that_runs_wake() -> None:
    written = shortcut.make(PYTHON)
    assert written == [shortcut.desktop() / shortcut.NAME, shortcut.start_menu() / shortcut.NAME]
    read = ("$l = (New-Object -ComObject WScript.Shell).CreateShortcut("
            f"'{written[0]}'); $l.TargetPath + '|' + $l.Arguments + '|' + $l.IconLocation")
    found = subprocess.run(["powershell", "-NoProfile", "-Command", read], capture_output=True,
                           text=True, check=True).stdout.strip()
    assert found == f"{PYTHON}|-P -m tarjim.wake|{shortcut.ICON},0"
