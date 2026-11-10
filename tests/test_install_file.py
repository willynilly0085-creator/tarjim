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
    command = installer.install_command("uv", "SOURCE", installer.Tested(
        Path("PINS"), Path("LIFTED"), "PYTHON"))
    for part in command[1:-1]:
        script_part = part.replace("PINS", "$pins").replace("LIFTED", "$lifted")
        assert script_part.replace("PYTHON", "$python") in script, part
    assert command[-1].replace("SOURCE", "$source") in script
    assert "raw.githubusercontent.com/$Repo/$($Matches[1])/tarjim/$name" in script
    for name in ("constraints.txt", "overrides.txt"):
        assert f'Get-Pins $source "{name}"' in script


def test_the_script_starts_the_engine_hidden_and_leaves_tests_alone() -> None:
    script = (ROOT / "scripts" / "windows" / "install.ps1").read_text(encoding="utf-8")
    assert "pythonw.exe" in script and "-WindowStyle Hidden" in script
    quiet = script[script.index("if (-not $Quiet)"):]
    for step in ("autostart.enable()", "shortcut.make()", "Start-Process $Page"):
        assert step in quiet, step


def test_the_last_step_runs_the_engines_python_not_a_version_number() -> None:
    """2026-11-10: `$python` holds "3.12"; used as a path it stopped the install before the
    shortcut, the start with the computer and the page."""
    script = (ROOT / "scripts" / "windows" / "install.ps1").read_text(encoding="utf-8")
    quiet = script[script.index("if (-not $Quiet)"):]
    assert 'Split-Path $engine) "python.exe"' in quiet
    assert "Split-Path $python" not in script


def test_a_dropped_connection_is_tried_again_before_the_person_has_to() -> None:
    script = (ROOT / "scripts" / "windows" / "install.ps1").read_text(encoding="utf-8")
    assert "Install-Engine $tested 3" in script and "Install-Engine @() 1" in script
    assert "| Out-Host" in script  # uv's lines are shown, not swallowed as the function's result
