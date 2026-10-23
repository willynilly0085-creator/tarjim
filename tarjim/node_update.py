"""tarjim's own Node.js, and the programs installed with it, keep themselves current.

Only the portable Node.js that tarjim put in ~/.tarjim/node for someone who had none (Windows,
engines/own_node.py); a Node.js the person installed is theirs and never touched. Once a day, with
automatic updates on, for the copy uv installed, while no job runs and no program is installing,
the engine reads nodejs.org's index.json: one request that carries nothing about the person.
When the newest LTS is newer than what node.exe reports, it is downloaded, checked against its
SHASUMS256.txt, unpacked beside the old folder, given the same programs at their latest, and only
then swapped in (engines/node_release.py). Any newer LTS is taken, not only those marked security:
fixes to npm and to the bundled libraries often arrive in releases that are not, a fresh install
gets the newest LTS anyway, and it is one 33 MB download every few weeks while nothing runs.
Otherwise the programs alone are brought to their latest. A failure leaves everything as it was,
is recorded in ~/.tarjim/node.json and is tried again the next day.
"""
import json
import subprocess
import time
from typing import Any

from tarjim import config, update
from tarjim.engines import app_install, node_release, own_node
from tarjim.installer import NO_WINDOW

CHECK_EVERY = 24 * 3600
FAILURES = node_release.FAILURES


def record(state: str, version: str, packages: list[str], detail: str = "") -> None:
    config.HOME.mkdir(parents=True, exist_ok=True)
    (config.HOME / "node.json").write_text(json.dumps(
        {"state": state, "version": version, "packages": packages, "detail": detail,
         "at": time.time()}), encoding="utf-8")


def progress() -> dict[str, Any]:
    try:
        return dict(json.loads((config.HOME / "node.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return {}


def allowed(idle: bool) -> bool:
    installing = any(app_install.installing(name) for name in list(app_install.running))
    return (idle and update.automatic() and update.installed_by_uv() and own_node.AVAILABLE
            and bool(own_node.node()) and not installing)


def due(now: float) -> bool:
    return now - float(config.setting("node_checked") or 0) >= CHECK_EVERY


def renew(version: str) -> str:
    """A newer Node.js with the same programs, or the old one as it was."""
    packages = own_node.packages()
    try:
        node_release.build(version, packages)
    except FAILURES as error:
        record("failed", version, packages, str(error))
        return ""
    record("done", version, packages)
    return version


def npm(action: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = [own_node.npm(), action, "-g", "--prefix", str(own_node.FOLDER), *arguments]
    return subprocess.run(command, capture_output=True, text=True,
                          timeout=node_release.NPM_SECONDS, env=own_node.environment(),
                          creationflags=NO_WINDOW, check=False)


def outdated() -> list[str]:
    """tarjim's programs that npm says have a newer release; npm itself stays the one Node.js
    shipped with."""
    try:
        listed = json.loads(npm("outdated", "--json").stdout or "{}")
    except (*FAILURES, TypeError):
        return []
    listed = listed if isinstance(listed, dict) else {}
    return [name for name in own_node.packages() if isinstance(listed.get(name), dict)
            and listed[name].get("current") != listed[name].get("latest")]


def refresh_programs(version: str) -> str:
    stale = outdated()
    if not stale:
        return ""
    try:
        done = npm("install", *(f"{name}@latest" for name in stale))
    except FAILURES as error:
        record("failed", version, stale, str(error))
        return ""
    detail = (done.stderr.strip().splitlines() or ["npm failed"])[-1] if done.returncode else ""
    record("failed" if done.returncode else "done", version, stale, detail)
    return "" if done.returncode else version


def refresh(idle: bool, now: float | None = None) -> str:
    """Called by the update watch; gives the version now in place when anything changed."""
    now = time.time() if now is None else now
    if not allowed(idle) or not due(now):
        return ""
    config.save("node_checked", str(now))
    own_node.recover()
    found = node_release.newest_lts(node_release.ask_index())
    if not found:
        return ""
    config.save("node_latest", found)
    have = own_node.version()  # a node.exe that no longer runs is replaced too
    stale = node_release.newer(found, have) or not node_release.number(have)
    return renew(found) if stale else refresh_programs(have)


def view() -> dict[str, Any]:
    if not own_node.node():
        return {"own": False}
    state = progress()
    return {"own": True, "version": own_node.version(), "latest": config.setting("node_latest"),
            "state": state.get("state", ""), "detail": state.get("detail", ""),
            "packages": state.get("packages", [])}
