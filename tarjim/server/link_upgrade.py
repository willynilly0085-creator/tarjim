"""Older versions added tarjim to Claude and Codex as `python -m tarjim.assistant`, which imports
a `tarjim` from whatever folder the chat tool is open in. The engine replaces those entries with
the current one when it starts; entries it did not write are left alone. The plain link to the
page that older installers put on the desktop is replaced the same way (tarjim/shortcut.py)."""
import json
import os
import tomllib
from pathlib import Path
from typing import Any

from tarjim import shortcut
from tarjim.engines.web import EngineError
from tarjim.server.assistant_link import NAME, desktop_config, link

OLD = ["-m", "tarjim.assistant"]


def places() -> dict[str, tuple[Path, str]]:
    claude = os.environ.get("CLAUDE_CONFIG_DIR")
    codex = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return {"claude-desktop": (desktop_config(), "mcpServers"),
            "claude-code": (Path(claude or Path.home()) / ".claude.json", "mcpServers"),
            "codex": (codex / "config.toml", "mcp_servers")}


def saved_args(path: Path, section: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
        return data[section][NAME]["args"]
    except (OSError, ValueError, LookupError, TypeError):
        return None


def refresh() -> list[str]:
    """The apps whose old entry was replaced."""
    shortcut.upgrade()
    replaced = []
    for app, (path, section) in places().items():
        try:
            if saved_args(path, section) == OLD and link(app)[0]:
                replaced.append(app)
        except (OSError, EngineError):
            continue
    return replaced
