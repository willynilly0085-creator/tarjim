"""tarjim's own Node.js, and the programs installed with it, keep themselves current: once a day,
with automatic updates on and nothing running, and never a Node.js the person installed."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, node_update, update
from tarjim.engines import app_install, node_release, own_node

INDEX = [{"version": "v24.22.1", "lts": "Krypton", "security": True, "files": ["win-x64-zip"]}]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(own_node, "FOLDER", tmp_path / "node")
    monkeypatch.setattr(own_node, "AVAILABLE", True)
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(own_node, "version", lambda: "v24.17.0")
    package = tmp_path / "node" / "node_modules" / "@openai" / "codex"
    package.mkdir(parents=True)
    (package / "package.json").write_text("{}", encoding="utf-8")
    for name in ("node.exe", "npm.cmd"):
        (tmp_path / "node" / name).write_text("", encoding="utf-8")
    app_install.running.clear()
    return tmp_path


def nodejs_org(monkeypatch: pytest.MonkeyPatch, index: Any = INDEX) -> list[str]:
    asked: list[str] = []

    def ask_index() -> Any:
        asked.append("index.json")
        return index

    monkeypatch.setattr(node_release, "ask_index", ask_index)
    return asked


def builds(monkeypatch: pytest.MonkeyPatch, error: Exception | None = None) -> list[Any]:
    made: list[Any] = []

    def build(version: str, packages: list[str]) -> None:
        made.append((version, packages))
        if error:
            raise error

    monkeypatch.setattr(node_release, "build", build)
    return made


def npm(monkeypatch: pytest.MonkeyPatch, outdated: Any, code: int = 0) -> list[list[str]]:
    commands: list[list[str]] = []

    class Done:
        def __init__(self, command: list[str]) -> None:
            listing = "outdated" in command
            self.returncode = 1 if listing and outdated else (0 if listing else code)
            self.stdout = json.dumps(outdated) if listing else ""
            self.stderr = "" if listing else "npm error EBUSY\n"

    def run(command: list[str], **_options: Any) -> Done:
        commands.append(command)
        return Done(command)

    monkeypatch.setattr(node_update.subprocess, "run", run)
    return commands


def test_a_newer_lts_replaces_tarjims_own_node_with_the_same_programs(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nodejs_org(monkeypatch)
    made = builds(monkeypatch)
    assert node_update.refresh(idle=True) == "v24.22.1"
    assert made == [("v24.22.1", ["@openai/codex"])]
    state = node_update.view()
    assert state["state"] == "done" and state["latest"] == "v24.22.1" and state["own"]
    assert update.view()["node"]["state"] == "done"


def test_a_failed_update_is_recorded_and_tried_again_the_next_day(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nodejs_org(monkeypatch)
    made = builds(monkeypatch, node_release.Refused("node-v24.22.1-win-x64.zip does not match"))
    assert node_update.refresh(idle=True, now=1_000_000.0) == ""
    state = node_update.progress()
    assert state["state"] == "failed" and "does not match" in state["detail"]
    assert state["version"] == "v24.22.1" and (home / "node" / "node.exe").is_file()
    assert node_update.refresh(idle=True, now=1_000_000.0 + 3600) == "" and len(made) == 1
    node_update.refresh(idle=True, now=1_000_000.0 + 25 * 3600)
    assert len(made) == 2


@pytest.mark.parametrize("have", ["v24.22.1", "v26.0.0"])
def test_a_current_node_is_kept_and_only_outdated_programs_are_updated(
        home: Path, monkeypatch: pytest.MonkeyPatch, have: str) -> None:
    monkeypatch.setattr(own_node, "version", lambda: have)
    nodejs_org(monkeypatch)
    made = builds(monkeypatch)
    outdated = {"@openai/codex": {"current": "0.40.0", "latest": "0.41.0"},
                "npm": {"current": "11.0.0", "latest": "12.0.0"}}
    commands = npm(monkeypatch, outdated)
    node_update.refresh(idle=True)
    folder = str(home / "node")
    assert made == [] and commands[-1] == [str(home / "node" / "npm.cmd"), "install", "-g",
                                           "--prefix", folder, "@openai/codex@latest"]
    assert node_update.progress()["packages"] == ["@openai/codex"]


def test_programs_already_current_are_left_alone(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(own_node, "version", lambda: "v24.22.1")
    nodejs_org(monkeypatch)
    commands = npm(monkeypatch, {})
    assert node_update.refresh(idle=True) == "" and len(commands) == 1
    assert node_update.progress() == {}


def test_a_failed_program_update_is_recorded(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(own_node, "version", lambda: "v24.22.1")
    nodejs_org(monkeypatch)
    npm(monkeypatch, {"@openai/codex": {"current": "0.40.0", "latest": "0.41.0"}}, code=1)
    node_update.refresh(idle=True)
    state = node_update.progress()
    assert state["state"] == "failed" and state["detail"] == "npm error EBUSY"


def test_nodejs_org_is_asked_at_most_once_a_day(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(own_node, "version", lambda: "v24.22.1")
    asked = nodejs_org(monkeypatch)
    npm(monkeypatch, {})
    node_update.refresh(idle=True, now=1_000_000.0)
    node_update.refresh(idle=True, now=1_000_000.0 + 3600)
    assert len(asked) == 1
    node_update.refresh(idle=True, now=1_000_000.0 + 25 * 3600)
    assert len(asked) == 2


@pytest.mark.parametrize("why", ["automatic off", "source copy", "job running", "installing",
                                 "not windows", "persons own node", "unreachable"])
def test_nothing_is_changed_unless_allowed_idle_and_tarjims_own(
        home: Path, monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    asked = nodejs_org(monkeypatch, [] if why == "unreachable" else INDEX)
    made, commands = builds(monkeypatch), npm(monkeypatch, {"@openai/codex": {"latest": "1"}})
    if why == "automatic off":
        config.save("auto_update", "no")
    if why == "source copy":
        monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    if why == "installing":
        live = type("Live", (), {"poll": lambda _self: None})()
        monkeypatch.setitem(app_install.running, "codex", live)
    if why == "not windows":
        monkeypatch.setattr(own_node, "AVAILABLE", False)
    if why == "persons own node":  # Node.js on PATH, no folder of tarjim's own
        (home / "node" / "node.exe").unlink()
    assert node_update.refresh(idle=why != "job running") == ""
    assert made == [] and commands == [] and node_update.progress() == {}
    assert asked == (["index.json"] if why == "unreachable" else [])


def test_the_page_shows_nothing_for_someone_without_tarjims_own_node(home: Path) -> None:
    (home / "node" / "node.exe").unlink()
    assert node_update.view() == {"own": False}
