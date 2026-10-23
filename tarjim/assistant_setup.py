"""What the chat plugin does before tarjim is running: report, install, start."""
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tarjim.assistant_http import SERVER
from tarjim.config import setting
from tarjim.installer import HOME, STATE, alive, module_command, safe_command, start_detached

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
        return safe_command(list(json.loads(saved)))
    found = shutil.which("tarjim-serve")
    return [found] if found else []


def launching(progress: dict[str, Any]) -> bool:
    started = float(progress.get("at", 0))
    return not progress.get("pid") and time.time() - started < LAUNCH_GRACE


KNOWN_ISSUES_NOTE = ("Published security issues in libraries installed with tarjim that still "
                     "apply to this install. Tell the person calmly, in their language: none is "
                     "reached by the way tarjim uses these libraries, and each one goes away by "
                     "itself when an update installs the fixed version.")


def library_issues() -> dict[str, Any]:
    """What the engine reports for its own installed versions (it alone can see them)."""
    from tarjim.assistant_http import call

    found = call("/update")
    issues = found.get("known_issues") if isinstance(found, dict) else None
    if not issues:
        return {}
    return {"known_library_issues": issues, "known_library_issues_note": KNOWN_ISSUES_NOTE,
            "known_library_issues_details": found.get("known_issues_details", "")}


LISTENING_NOTE = ("Local listening works with its earlier models while their newer version "
                  "downloads; the newer one takes over by itself. 'manual' means automatic updates "
                  "are off: install_tool('accuracy') fetches it.")


def listening_update() -> dict[str, Any]:
    """The newer listening models' download, while the earlier ones still listen."""
    from tarjim.assistant_http import call

    tools = call("/tools")
    found = [t for t in tools if t.get("upgrade")] if isinstance(tools, list) else []
    if not found:
        return {}
    return {"listening_models_update": found[0]["upgrade"], "listening_models_note": LISTENING_NOTE,
            "listening_models_gb": found[0].get("size_gb")}


def status() -> dict[str, Any]:
    page = f"{setting('server') or SERVER}/"
    if running():
        return {"engine": "running", "page": page, **library_issues(), **listening_update()}
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
    command = [*module_command("tarjim.installer"), source()]
    start_detached(command, HOME / "installer-output.log")
    return {"engine": "installing", "detail": "This takes several minutes; ask for the status."}


def start() -> dict[str, Any]:
    if running():
        return status()
    command = server_command()
    if not command:
        return {"engine": "missing", "next": "call install_tarjim"}
    start_detached(command, HOME / "server.log")
    return {"engine": "starting", "page": f"{setting('server') or SERVER}/"}
