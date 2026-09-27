"""What the chat plugin does before tarjim is running: report, install, start."""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tarjim.assistant_http import SERVER
from tarjim.config import setting
from tarjim.installer import HOME, STATE, alive, start_detached

OK = 200
LAUNCH_GRACE = 120.0


def running() -> bool:
    try:
        with urllib.request.urlopen(f"{setting('server') or SERVER}/ping", timeout=3) as reply:
            return bool(reply.status == OK)
    except (urllib.error.URLError, OSError):
        return False


def installing() -> dict[str, Any]:
    try:
        return dict(json.loads(STATE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def server_command() -> list[str]:
    saved = setting("server_command")
    if saved:
        return list(json.loads(saved))
    found = shutil.which("tarjim-serve")
    return [found] if found else []


def launching(progress: dict[str, Any]) -> bool:
    started = float(progress.get("at", 0))
    return not progress.get("pid") and time.time() - started < LAUNCH_GRACE


def status() -> dict[str, Any]:
    page = f"{setting('server') or SERVER}/"
    if running():
        return {"engine": "running", "page": page}
    progress = installing()
    if progress.get("state") == "installing":
        if alive(int(progress.get("pid", 0))) or launching(progress):
            return {"engine": "installing", "detail": progress.get("detail", "")}
        progress = {"state": "failed", "detail": "the installer stopped; call install_tarjim again"}
    if server_command():
        return {"engine": "installed but stopped", "next": "call start_tarjim"}
    return {"engine": "missing", "next": "call install_tarjim", **progress}


def source() -> str:
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if plugin and (Path(plugin) / "pyproject.toml").exists():
        return Path(plugin).resolve().as_uri()
    return os.environ.get("TARJIM_SOURCE", "")


def install() -> dict[str, Any]:
    if running():
        return status()
    if not source():
        return {"engine": "missing", "detail": "install the tarjim plugin, or set TARJIM_SOURCE"}
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"state": "installing", "detail": "starting the installer",
                                 "pid": 0, "at": time.time()}), encoding="utf-8")
    start_detached([sys.executable, "-m", "tarjim.installer", source()], HOME / "install.log")
    return {"engine": "installing", "detail": "This takes several minutes; ask for the status."}


def start() -> dict[str, Any]:
    if running():
        return status()
    command = server_command()
    if not command:
        return {"engine": "missing", "next": "call install_tarjim"}
    start_detached(command, HOME / "server.log")
    return {"engine": "starting", "page": f"{setting('server') or SERVER}/"}
