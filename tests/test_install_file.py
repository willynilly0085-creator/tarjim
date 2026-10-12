"""The one file a new person double-clicks: it must exist, point at its script, and install the
same thing the engine's own installer does."""
from pathlib import Path

from tarjim import installer

ROOT = Path(__file__).resolve().parents[1]


def test_the_install_file_runs_the_script_that_ships_beside_it() -> None:
    launcher = (ROOT / "install.cmd").read_text(encoding="utf-8")
    assert r"scripts\windows\install.ps1" in launcher and "-ExecutionPolicy Bypass" in launcher
    assert (ROOT / "scripts" / "windows" / "install.ps1").is_file()


def test_the_script_installs_what_the_engines_installer_installs() -> None:
    script = (ROOT / "scripts" / "windows" / "install.ps1").read_text(encoding="utf-8")
    command = installer.install_command("uv", "SOURCE")
    for part in command[1:-1]:
        assert part in script, part
    assert command[-1].replace("SOURCE", "$source") in script


def test_the_script_starts_the_engine_hidden_and_leaves_tests_alone() -> None:
    script = (ROOT / "scripts" / "windows" / "install.ps1").read_text(encoding="utf-8")
    assert "pythonw.exe" in script and "-WindowStyle Hidden" in script
    quiet = script[script.index("if (-not $Quiet)"):]
    for step in ("autostart.enable()", "Add-Shortcut", "Start-Process $Page"):
        assert step in quiet, step
