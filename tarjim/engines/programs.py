"""Find a program the way a newly opened terminal would.

tarjim keeps running in the background, so the PATH it was started with goes stale: a program the
person installs afterwards (Claude Code, Node.js, anything) is on the computer's PATH but not on
tarjim's. Windows keeps the current PATH in the registry, so that is read on every miss; npm's own
folder is added because npm does not always put it on PATH.
"""
import os
import shutil
import sys
from pathlib import Path

PLACES = (("HKEY_CURRENT_USER", "Environment"),
          ("HKEY_LOCAL_MACHINE", r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"))


def stored(root: str, key: str) -> str:
    if sys.platform != "win32":
        return ""
    import winreg

    try:
        with winreg.OpenKey(getattr(winreg, root), key) as opened:
            return os.path.expandvars(str(winreg.QueryValueEx(opened, "Path")[0]))
    except OSError:
        return ""


def current_path() -> str:
    """The PATH a terminal opened right now would get, plus npm's folder for global programs."""
    if sys.platform != "win32":
        return os.environ.get("PATH", "")
    npm = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "npm"
    return os.pathsep.join([*(stored(root, key) for root, key in PLACES), str(npm)])


def find(name: str) -> str | None:
    return shutil.which(name) or shutil.which(name, path=current_path())
