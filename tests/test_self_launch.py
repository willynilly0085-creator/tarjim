"""tarjim starts itself in folders it does not choose (the one a chat tool is open in). A `tarjim`
package or `tarjim.py` sitting there must never be imported in place of tarjim."""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tarjim import assistant_setup, autostart, installer
from tarjim.server import assistant_link

ROOT = Path(__file__).resolve().parent.parent


def runs_a_strangers_tarjim(flags: list[str], module: str, folder: Path) -> bool:
    """Start tarjim with these flags from a folder that carries its own `tarjim.py`."""
    marker = folder / "ran.txt"
    (folder / "tarjim.py").write_text(f"open({str(marker)!r}, 'w').write('ran')\n")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    subprocess.run([sys.executable, *flags, module, "--help"], cwd=folder, env=env,
                   capture_output=True, timeout=60, stdin=subprocess.DEVNULL, check=False)
    return marker.exists()


def test_the_chat_entry_ignores_a_tarjim_in_the_open_folder(tmp_path: Path) -> None:
    entry = assistant_link.server_entry()
    assert entry[-1] == "tarjim.assistant"
    assert not runs_a_strangers_tarjim(entry[1:-1], "tarjim.installer", tmp_path)


def test_the_plugin_ignores_a_tarjim_in_the_open_folder(tmp_path: Path) -> None:
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    args = plugin["mcpServers"]["tarjim"]["args"]
    flags = args[args.index("python") + 1:-1]
    assert args[-1] == "tarjim.assistant"
    assert not runs_a_strangers_tarjim(flags, "tarjim.installer", tmp_path)


@pytest.fixture
def started(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    commands: list[list[str]] = []
    monkeypatch.setattr(assistant_setup, "HOME", tmp_path)
    monkeypatch.setattr(assistant_setup, "STATE", tmp_path / "install.json")
    monkeypatch.setattr(assistant_setup, "running", lambda: False)
    monkeypatch.setattr(assistant_setup, "start_detached",
                        lambda command, _log: commands.append(command))
    return commands


def test_installing_from_chat_ignores_a_tarjim_in_the_open_folder(
        started: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_setup, "source", lambda: "file:///plugin")
    assistant_setup.install()
    command = started[0]
    assert command[-2:] == ["tarjim.installer", "file:///plugin"]
    assert not runs_a_strangers_tarjim(command[1:-2], "tarjim.installer", tmp_path)


def test_a_start_command_saved_by_an_older_version_is_made_safe(
        started: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    old = {"server_command": json.dumps(["/py/python", "-m", "tarjim.server"])}
    monkeypatch.setattr(assistant_setup, "setting", lambda key: old.get(key, ""))
    assistant_setup.start()
    assert started == [["/py/python", "-P", "-m", "tarjim.server"]]


def test_the_engine_saves_a_safe_start_command(monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.server import engine

    saved: dict[str, str] = {}
    monkeypatch.setattr("tarjim.quiet.hide_child_windows", lambda: None)
    monkeypatch.setattr(engine, "attach_output", lambda: None)
    monkeypatch.setattr(autostart, "refresh", lambda: None)
    monkeypatch.setattr(engine, "prepare_environment", lambda: None)
    monkeypatch.setattr(engine, "save", lambda key, value: saved.update({key: value}))
    engine.start_up()
    assert json.loads(saved["server_command"])[1:] == ["-P", "-m", "tarjim.server"]


@pytest.mark.parametrize("write", [autostart.windows_script, autostart.mac_agent,
                                   autostart.linux_entry])
def test_starting_with_the_computer_ignores_the_current_folder(write: Any) -> None:
    text = write("/py/pythonw.exe")
    assert "-P" in text and text.index("-P") < text.rindex("tarjim.server")


def test_programs_tarjim_starts_run_in_its_folder_without_relative_import_paths(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(installer.sys, "platform", "linux")
    monkeypatch.setattr(installer.subprocess, "Popen", lambda *_a, **kw: seen.update(kw))
    plugin = str(tmp_path / "plugin")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(["", plugin, ".", "lib"]))
    installer.start_detached(["program"], tmp_path / "out.log")
    assert seen["cwd"] == tmp_path
    assert seen["env"]["PYTHONPATH"] == plugin


def test_the_windows_launch_line_drops_relative_import_paths(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in installer.KEEP_ENV:  # CI's uv setup sets UV_TOOL_DIR, for one
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHONPATH", os.pathsep + "lib")
    line = installer.windows_line(["python"], tmp_path / "i.log")
    assert line.startswith('cmd /d /s /c "set "PYTHONPATH="&& python ')
