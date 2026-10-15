"""yt-dlp keeps itself current, apart from tarjim's releases.

Sites change every few weeks and an old yt-dlp stops downloading from them. Once a day, with
automatic updates on and for the copy uv installed, the engine asks PyPI for yt-dlp's latest
version: one request that carries nothing about the person. A newer one is installed into
tarjim's own environment while nothing downloads, and the next download uses it. A failure
leaves the installed yt-dlp as it was and is recorded in ~/.tarjim/downloader.json.
"""
import importlib
import json
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from tarjim import config, pins, update
from tarjim.fetch import IN_USE
from tarjim.installer import NO_WINDOW

PYPI = "https://pypi.org/pypi/yt-dlp/json"
CHECK_EVERY = 24 * 3600
ASK_SECONDS = 15
INSTALL_SECONDS = 600
RELEASE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d{1,6}))?")


def release(text: str) -> tuple[int, ...]:
    """yt-dlp's version as numbers; anything but a plain release number gives nothing."""
    match = RELEASE.fullmatch(text) if isinstance(text, str) else None
    return tuple(int(part) for part in match.groups() if part is not None) if match else ()


def newer(found: str, have: str) -> bool:
    return bool(release(found)) and bool(release(have)) and release(found) > release(have)


def ask_pypi() -> str:
    import requests

    try:
        reply = requests.get(PYPI, timeout=ASK_SECONDS, headers={"Accept": "application/json"})
        found = reply.json()["info"]["version"] if reply.ok else ""
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return ""
    return found if isinstance(found, str) and release(found) else ""


def latest(now: float) -> str:
    """The latest known yt-dlp, asking PyPI at most once a day."""
    if now - float(config.setting("ytdlp_checked") or 0) >= CHECK_EVERY:
        found = ask_pypi()
        config.save("ytdlp_checked", str(now))
        if found:
            config.save("ytdlp_latest", found)
    return config.setting("ytdlp_latest")


def installed() -> str:
    return pins.installed("yt-dlp")


def command(uv: str, version: str) -> list[str]:
    """The environment is named by its folder: on Windows the engine may run as pythonw. The
    tested versions keep every other library where the release put it."""
    if not release(version):
        raise ValueError(f"not a yt-dlp version: {version!r}")
    tested = ["-c", str(pins.FILE)] if pins.FILE.is_file() else []
    tested += ["--overrides", str(pins.OVERRIDES)] if tested and pins.OVERRIDES.is_file() else []
    return [uv, "pip", "install", "--python", sys.prefix, *tested, f"yt-dlp=={version}"]


def record(state: str, version: str, detail: str = "") -> None:
    config.HOME.mkdir(parents=True, exist_ok=True)
    (config.HOME / "downloader.json").write_text(json.dumps(
        {"state": state, "version": version, "detail": detail, "at": time.time()}),
        encoding="utf-8")


def progress() -> dict[str, Any]:
    try:
        return dict(json.loads((config.HOME / "downloader.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def forget() -> None:
    """The next download imports the new yt-dlp instead of the copy already loaded."""
    for name in [name for name in sys.modules if name.split(".")[0] == "yt_dlp"]:
        del sys.modules[name]
    importlib.invalidate_caches()


def install(version: str) -> bool:
    try:
        done = subprocess.run(command(shutil.which("uv") or "uv", version), capture_output=True,
                              text=True, timeout=INSTALL_SECONDS, creationflags=NO_WINDOW,
                              check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        record("failed", version, str(error))
        return False
    if done.returncode:
        record("failed", version, (done.stderr.strip().splitlines() or ["uv failed"])[-1])
        return False
    forget()
    record("done", version)
    return True


def tried_lately(version: str, now: float) -> bool:
    """A version that failed to install is tried again the next day, not every hour."""
    state = progress()
    return (state.get("state") == "failed" and state.get("version") == version
            and now - float(state.get("at") or 0) < CHECK_EVERY)


def refresh(idle: bool, now: float | None = None) -> str:
    """Called by the update watch; gives the version installed, or nothing."""
    if not (idle and update.automatic() and update.installed_by_uv()):
        return ""
    now = time.time() if now is None else now
    found = latest(now)
    if not newer(found, installed()) or tried_lately(found, now):
        return ""
    if not IN_USE.acquire(blocking=False):
        return ""
    try:
        return found if install(found) else ""
    finally:
        IN_USE.release()


def view() -> dict[str, Any]:
    state = progress()
    return {"version": installed(), "latest": config.setting("ytdlp_latest"),
            "state": state.get("state", ""), "detail": state.get("detail", "")}
