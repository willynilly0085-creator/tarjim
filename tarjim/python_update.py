"""The Python under tarjim's environment keeps itself current, and moves when a release asks.

Which Python a release runs on is in tarjim/python.txt ("the target" below). uv installs tarjim
with `--python <target>` and takes whatever patch it finds or has then, so its security releases
never arrive by themselves. Once a day, with automatic updates on, for the copy uv installed,
while no job runs and nothing installs, the engine asks uv for the newest CPython of the target
it offers (`uv python list <target> --only-downloads`, read from uv itself, so it moves with uv)
and compares it with the Python the engine runs on. When it is newer, uv installs it (no
executable on the path, nothing in the registry, so nothing else on the computer changes) and the
engine hands over to the updater it uses for its own releases (update.start, the same tag and
tested versions), which rebuilds the environment: uv prefers the newest Python it manages, and
recreates an environment whose interpreter is not that one, keeping it as it was when the install
cannot be resolved. The rebuild is started at most once for each new patch, so it cannot loop;
`/update` shows under `python` whether the engine came back on it.

An engine on another Python than the target (a release moved tarjim to a newer one while an
older installer, which knew only 3.11, installed it) moves the same way. A copy run from source
moves too (source_updater.py makes its environment again), but takes no patch releases: its
owner keeps those.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from tarjim import __version__, config, pins, update
from tarjim.installer import NO_WINDOW

CHECK_EVERY = 24 * 3600
THREE = 3  # Python 3
ASK_SECONDS = 60
INSTALL_SECONDS = 900
CPYTHON = {"implementation": "cpython", "variant": "default"}


def target() -> str:
    return pins.python()


def patch(version: object) -> int:
    """The patch of exactly <target>.N, or -1 for anything else (another Python too)."""
    pattern = re.escape(target()) + r"\.([0-9]{1,3})"
    match = re.fullmatch(pattern, version) if isinstance(version, str) else None
    return int(match[1]) if match else -1


def newer(found: str, have: str) -> bool:
    """A newer patch of the target, or the target at all when this runs on another Python."""
    return bool(have) and patch(found) > patch(have)


def moving() -> bool:
    return bool(running()) and patch(running()) < 0


def offered(entry: object) -> str:
    """A plain CPython download of the target, not PyPy, GraalPy, free-threaded or debug."""
    if not isinstance(entry, dict) or any(entry.get(k) != v for k, v in CPYTHON.items()):
        return ""
    version = entry.get("version")
    return version if isinstance(version, str) and patch(version) >= 0 else ""


def newest(listing: object) -> str:
    found = [version for version in map(offered, listing if isinstance(listing, list) else [])
             if version]
    return max(found, key=patch, default="")


def running() -> str:
    here = sys.version_info
    plain = sys.implementation.name == "cpython" and here[0] == THREE
    return f"{here[0]}.{here[1]}.{here[2]}" if plain else ""


def uv(*arguments: str, seconds: int = ASK_SECONDS) -> subprocess.CompletedProcess[str]:
    return subprocess.run([shutil.which("uv") or "uv", *arguments], capture_output=True,
                          text=True, timeout=seconds, creationflags=NO_WINDOW, check=False)


def ask_uv() -> Any:
    try:
        return json.loads(uv("python", "list", target(), "--only-downloads", "--output-format",
                             "json").stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def record(state: str, version: str, detail: str = "") -> None:
    config.HOME.mkdir(parents=True, exist_ok=True)
    (config.HOME / "python.json").write_text(json.dumps(
        {"state": state, "version": version, "detail": detail, "at": time.time()}),
        encoding="utf-8")


def progress() -> dict[str, Any]:
    try:
        return dict(json.loads((config.HOME / "python.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return {}


def busy() -> bool:
    from tarjim import tools
    from tarjim.engines import app_install

    return bool(tools.DOWNLOADING) or any(map(app_install.installing, list(app_install.running)))


def allowed(idle: bool) -> bool:
    mine = update.installed_by_uv() or (update.from_source() and moving())
    return idle and update.automatic() and mine and bool(running()) and not busy()


def due(now: float) -> bool:
    return now - float(config.setting("python_checked") or 0) >= CHECK_EVERY


def install(version: str) -> bool:
    """The new patch beside the old ones, managed by uv only."""
    if patch(version) < 0:
        raise ValueError(f"not a Python {target()} version: {version!r}")
    quiet = ["--no-bin", *(["--no-registry"] if sys.platform == "win32" else [])]
    try:
        done = uv("python", "install", version, *quiet, seconds=INSTALL_SECONDS)
    except (OSError, subprocess.SubprocessError) as error:
        record("failed", version, str(error))
        return False
    if done.returncode:
        record("failed", version, (done.stderr.strip().splitlines() or ["uv failed"])[-1])
    return done.returncode == 0


def rebuild(version: str, port: int) -> bool:
    """Once per patch: the updater rebuilds the environment and starts the engine again."""
    config.save("python_rebuilt_for", version)
    record("rebuilding", version)
    started = update.start(f"v{__version__}", port)
    if not started:
        record("failed", version, "the updater did not start")
    return started


def refresh(idle: bool, port: int, now: float | None = None) -> bool:
    """Called by the update watch; True when the engine must now close for the rebuild."""
    now = time.time() if now is None else now
    if not allowed(idle) or not due(now):
        return False
    config.save("python_checked", str(now))
    found = newest(ask_uv())
    if found:
        config.save("python_latest", found)
    if not newer(found, running()) or config.setting("python_rebuilt_for") == found:
        return False
    return install(found) and rebuild(found, port)


def settled(state: dict[str, Any]) -> str:
    """A rebuild's outcome, known once the updater finished and the engine runs again."""
    if state.get("version") == running():
        return "done"
    return "failed" if update.progress().get("state") in ("done", "failed") else "rebuilding"


def view() -> dict[str, Any]:
    state = progress()
    said, detail = state.get("state", ""), state.get("detail", "")
    if said == "rebuilding":
        said = settled(state)
        detail = f"the engine still runs on {running()}" if said == "failed" else ""
    return {"version": running(), "latest": config.setting("python_latest"), "state": said,
            "target": state.get("version", ""), "detail": detail}
