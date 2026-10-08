"""Know when a newer tarjim has been released, and replace this one with it.

Once a day the engine asks GitHub for the number of the latest release: one request that carries
nothing about the person or their videos. With automatic updates on (the person's choice), a newer
release is installed when no job is running; otherwise the page offers a button. An update needs
the copy that uv installed; a copy run from source is updated with git instead.
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from tarjim import __version__, config

REPO = "willynilly0085-creator/tarjim"
RELEASES = os.environ.get("TARJIM_RELEASES", f"https://api.github.com/repos/{REPO}/releases/latest")
ARCHIVE = os.environ.get("TARJIM_ARCHIVE", f"https://github.com/{REPO}/archive/refs/tags/{{tag}}.zip")
CHECK_EVERY = 24 * 3600
TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
ASK_SECONDS = 15


def number(tag: str) -> tuple[int, ...]:
    match = TAG.match(tag.strip())
    return tuple(int(part) for part in match.groups()) if match else ()


def newer(latest: str) -> bool:
    return bool(number(latest)) and number(latest) > number(__version__)


def ask_latest() -> str:
    """The latest release's tag, or nothing when GitHub cannot be reached."""
    import requests

    try:
        reply = requests.get(RELEASES, timeout=ASK_SECONDS,
                             headers={"Accept": "application/vnd.github+json"})
        tag = str(reply.json().get("tag_name", "")) if reply.ok else ""
    except (requests.RequestException, ValueError):
        return ""
    return tag if number(tag) else ""


def latest(now: float | None = None) -> str:
    """The latest known release, asking GitHub at most once a day."""
    now = time.time() if now is None else now
    if now - float(config.setting("update_checked") or 0) >= CHECK_EVERY:
        found = ask_latest()
        config.save("update_checked", str(now))
        if found:
            config.save("update_latest", found)
    return config.setting("update_latest")


def installed_by_uv() -> bool:
    """uv leaves a receipt in the environment of every tool it installs."""
    return (Path(sys.prefix) / "uv-receipt.toml").is_file() and bool(shutil.which("uv"))


def automatic() -> bool:
    return config.setting("auto_update") != "no"


def progress() -> dict[str, Any]:
    try:
        return dict(json.loads((config.HOME / "update.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def extension_version() -> str:
    """The browser extension shipped with this engine; the extension reloads itself to match."""
    from tarjim.extension_home import MANIFEST, PACKAGED

    try:
        return str(json.loads((PACKAGED / MANIFEST).read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return ""


def view() -> dict[str, Any]:
    found = latest()
    return {"current": __version__, "latest": found.lstrip("v"), "available": newer(found),
            "automatic": automatic(), "can_install": installed_by_uv(),
            "failed": newer(found) and progress().get("state") == "failed",
            "extension": extension_version()}


def archive(tag: str) -> str:
    return ARCHIVE.format(tag=tag)


def start(tag: str, port: int) -> bool:
    """Hand over to a copy of the installer that runs outside this engine's folder. The caller
    must then close the engine: the installer waits for that before replacing its files."""
    from tarjim import installer

    uv = shutil.which("uv")
    if not uv or not installed_by_uv() or not number(tag):
        return False
    copy = config.HOME / "updater.py"
    shutil.copyfile(installer.__file__, copy)
    installer.record("starting", tag, installer.UPDATE_STATE)
    command = [uv, "run", "--quiet", "--no-project", "--python", "3.11", "python", str(copy),
               archive(tag), "--after", str(os.getpid()), "--port", str(port)]
    installer.start_detached(command, config.HOME / "update.log")
    return True
