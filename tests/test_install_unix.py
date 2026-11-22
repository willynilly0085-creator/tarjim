"""The one line a Mac or Linux user pastes: it installs what the Windows script installs, and
the engine it leaves finds its programs and writes its log when it starts with the computer."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tarjim import autostart, installer

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "unix" / "install.sh"


def test_the_script_installs_what_the_engines_installer_installs() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    command = installer.install_command("uv", "SOURCE", installer.Tested(
        Path("PINS"), Path("LIFTED"), "PYTHON"))
    assert "uv tool install --force --python \"$PYTHON\" --torch-backend auto" in script
    assert command[-1].replace("SOURCE", "$SOURCE") in script
    for name in ("constraints.txt", "overrides.txt", "python.txt"):
        assert f'release_file "$SOURCE" {name}' in script
    assert "raw.githubusercontent.com/$REPO/$tag/tarjim/$2" in script


def test_tests_leave_the_computer_as_it_is() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    quiet = script[script.index('if [ -z "${TARJIM_QUIET:-}" ]'):]
    assert "autostart.enable()" in quiet and 'open "$PAGE"' in quiet
    assert "autostart" not in script[:script.index('if [ -z "${TARJIM_QUIET:-}" ]')]


@pytest.mark.skipif(sys.platform == "win32" or not shutil.which("bash"),
                    reason="needs bash (Windows' bash.exe is WSL's)")
def test_the_script_is_valid_bash() -> None:
    done = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True,
                          check=False)
    assert done.returncode == 0, done.stderr
    assert SCRIPT.read_bytes().count(b"\r") == 0  # a Windows line end breaks bash


def test_on_a_mac_the_engine_finds_its_programs_and_writes_its_log() -> None:
    """2026-11-20, the owner's Mac: started with the computer, the engine got launchd's bare PATH
    (no ~/.local/bin, where uv, agy, claude and ffmpeg were) and its output went nowhere."""
    plist = autostart.mac_agent("/py/python")
    assert "<key>EnvironmentVariables</key>" in plist
    assert str(Path.home() / ".local" / "bin") + ":" in plist
    assert "/opt/homebrew/bin" in plist and "/usr/bin:/bin" in plist
    assert plist.count("server.log") == 2  # what it prints, and its errors
