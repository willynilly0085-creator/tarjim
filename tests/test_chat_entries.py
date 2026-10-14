"""Entries older versions added to Claude and Codex are replaced with the current, safe one."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim.server import assistant_link, link_upgrade

OLD = ["-m", "tarjim.assistant"]


@pytest.fixture
def ran(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    from tarjim.engines import subscription

    commands: list[list[str]] = []

    def run(command: list[str], *_args: Any, **_kw: Any) -> Any:
        commands.append(command)
        return subscription.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subscription, "launcher", lambda name: [name])
    monkeypatch.setattr(subscription, "run", run)
    monkeypatch.setattr(link_upgrade.Path, "home", lambda: tmp_path)
    for name in ("APPDATA", "CLAUDE_CONFIG_DIR", "CODEX_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    return commands


def test_adding_again_replaces_the_entry_instead_of_keeping_the_old_one(
        ran: list[list[str]]) -> None:
    assert assistant_link.link("claude-code")[0]
    assert ran[0] == ["claude", "mcp", "remove", "--scope", "user", "tarjim"]
    assert ran[1][:5] == ["claude", "mcp", "add", "--scope", "user"]
    assert ran[1][-3:] == ["-P", "-m", "tarjim.assistant"]


def test_old_claude_code_and_codex_entries_are_replaced(ran: list[list[str]],
                                                        tmp_path: Path) -> None:
    entry = {"command": "/py/python.exe", "args": OLD}
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"tarjim": entry}}))
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text(
        '[mcp_servers.tarjim]\ncommand = "/py/python"\nargs = ["-m", "tarjim.assistant"]\n')
    assert link_upgrade.refresh() == ["claude-code", "codex"]
    assert [c[:3] for c in ran] == [["claude", "mcp", "remove"], ["claude", "mcp", "add"],
                                    ["codex", "mcp", "remove"], ["codex", "mcp", "add"]]


def test_an_old_claude_app_entry_is_replaced(ran: list[list[str]], tmp_path: Path) -> None:
    settings = tmp_path / ".config" / "Claude" / "claude_desktop_config.json"
    settings.parent.mkdir(parents=True)
    entries = {"tarjim": {"command": "/py/python", "args": OLD}, "other": {"command": "x"}}
    settings.write_text(json.dumps({"mcpServers": entries}))
    assert link_upgrade.refresh() == ["claude-desktop"]
    saved = json.loads(settings.read_text(encoding="utf-8"))["mcpServers"]
    assert saved["tarjim"]["args"] == ["-P", "-m", "tarjim.assistant"] and "other" in saved


def test_current_or_foreign_entries_are_left_alone(ran: list[list[str]], tmp_path: Path) -> None:
    mine = {"command": "/py/python", "args": ["-P", "-m", "tarjim.assistant"]}
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"tarjim": mine}}))
    (tmp_path / ".codex").mkdir()
    codex = '[mcp_servers.tarjim]\ncommand = "tarjim-mcp"\n'
    (tmp_path / ".codex" / "config.toml").write_text(codex)
    assert link_upgrade.refresh() == [] and ran == []
