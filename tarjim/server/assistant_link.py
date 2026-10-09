"""Add tarjim to Claude (the app or Claude Code) or to Codex, so people can use it in chat."""
import json
import os
import sys
from pathlib import Path

NAME = "tarjim"
APPS = ("claude-desktop", "claude-code", "codex")


def python_for_chat() -> str:
    console = Path(sys.executable).with_name("python.exe")
    return str(console) if console.exists() else sys.executable


def server_entry() -> list[str]:
    return [python_for_chat(), "-m", "tarjim.assistant"]


def desktop_config() -> Path:
    mac = Path.home() / "Library" / "Application Support"
    unix = mac if sys.platform == "darwin" else Path(
        os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return Path(os.environ.get("APPDATA") or unix) / "Claude" / "claude_desktop_config.json"


def link_desktop() -> tuple[bool, str]:
    path = desktop_config()
    try:
        config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return False, "could not read the Claude settings file"
    command, *args = server_entry()
    config.setdefault("mcpServers", {})[NAME] = {"command": command, "args": args}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, "restart the Claude app to see tarjim"


def link_program(program: str, extra: list[str]) -> tuple[bool, str]:
    from tarjim.engines.subscription import launcher, run

    base = launcher(program)
    if not base:
        return False, f"{program} is not installed"
    done = run([*base, "mcp", "add", *extra, NAME, "--", *server_entry()], "", str(Path.home()))
    text = (done.stdout + done.stderr).strip()[-300:]
    return done.returncode == 0 or "already exists" in text, text


def link(app: str) -> tuple[bool, str]:
    if app == "claude-desktop":
        return link_desktop()
    if app == "claude-code":
        return link_program("claude", ["--scope", "user"])
    if app == "codex":
        return link_program("codex", [])
    return False, "unknown app"

