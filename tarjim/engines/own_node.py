"""Node.js of tarjim's own, for subscription programs that are npm packages (Codex, Copilot).

A person with no Node.js is not sent to install it: on Windows tarjim downloads the official
portable build from nodejs.org into its own folder, checked against Node's published SHA-256
(node_release), and installs the package beside it, so nothing else on the computer changes.
node_update keeps that folder current. Elsewhere the page still links to the Node.js download.
A Node.js the person installed is never touched: only ~/.tarjim/node is ever replaced.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tarjim.config import HOME

FOLDER = HOME / "node"
AVAILABLE = sys.platform == "win32"
HIDDEN = 0x08000000 if sys.platform == "win32" else 0
SETUP = "tarjim.engines.node_setup"


def npm() -> str:
    found = FOLDER / "npm.cmd"
    return str(found) if found.is_file() else ""


def scripts_for(packages: list[str]) -> str:
    """npm 12 runs no package's install script unless it is named: Claude Code's fetches its
    program, and without it `claude` only says its program is not installed (2026-10-31). Older
    npm warns about the option it does not know and goes on."""
    return "--allow-scripts=" + ",".join(p[0] + p[1:].split("@")[0] for p in packages)


def node() -> str:
    found = FOLDER / "node.exe"
    return str(found) if found.is_file() else ""


def shim(name: str) -> str | None:
    found = FOLDER / f"{name}.cmd"
    return str(found) if found.is_file() else None


def version() -> str:
    """What tarjim's own node.exe says it is, or nothing when there is none or it does not run."""
    if not node():
        return ""
    try:
        done = subprocess.run([node(), "--version"], capture_output=True, text=True, timeout=15,
                              creationflags=HIDDEN, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def install(package: str) -> list[str]:
    """Add the package with tarjim's own Node.js, downloading and checking that first when it is
    missing (node_setup, run by this same Python so the check is tarjim's own code)."""
    if npm():
        return [npm(), "install", "-g", "--prefix", str(FOLDER), scripts_for([package]), package]
    return [sys.executable, "-P", "-m", SETUP, package]


def environment(folder: Path | None = None) -> dict[str, str]:
    """npm's own scripts call `node`, so tarjim's folder is on the path while it installs."""
    first = FOLDER if folder is None else folder
    return {**os.environ, "PATH": f"{first}{os.pathsep}{os.environ.get('PATH', '')}"}


def packages() -> list[str]:
    """The programs tarjim installed into its own Node.js (never npm or corepack themselves)."""
    from tarjim.engines.app_install import PACKAGES

    return [name for name in PACKAGES.values()
            if (FOLDER / "node_modules" / name / "package.json").is_file()]


def staging() -> Path:
    return FOLDER.with_name("node-new")


def retired() -> Path:
    return FOLDER.with_name("node-old")


def recover() -> None:
    """A swap cut short between its two renames leaves only the old folder: it goes back. With
    the new one in place, an old folder left behind (a program was still running from it) goes."""
    if not FOLDER.exists() and retired().is_dir():
        retired().rename(FOLDER)
    shutil.rmtree(retired(), ignore_errors=True)


def swap(ready: Path) -> None:
    """The new folder takes the old one's place; when it cannot, the old one stays where it was.
    Windows lets a folder be renamed while a program runs from it: that program keeps running from
    node-old and new starts use the new folder. If node-old cannot be cleared yet, nothing moves."""
    recover()
    if FOLDER.exists():
        FOLDER.rename(retired())
    try:
        ready.rename(FOLDER)
    except OSError:
        recover()
        raise
    shutil.rmtree(retired(), ignore_errors=True)
