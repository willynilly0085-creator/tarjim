"""tarjim's own ffmpeg keeps itself current (Windows).

Only the build tarjim put in ~/.tarjim/tools/ffmpeg for someone who had no ffmpeg
(ffmpeg_setup.py), and only while the saved ffmpeg and ffprobe both point there with nothing set
in TARJIM_FFMPEG or TARJIM_FFPROBE: an ffmpeg the person installed or chose is theirs and never
touched. BtbN rebuilds its release branches every day with the branch's fixes, so the version
number says little; the build's published SHA-256 says whether it changed. Once a day, with
automatic updates on, for the copy uv installed, while no job runs, the engine reads
checksums.sha256 (one request that carries nothing about the person). When the digest for the
branch in use differs from the one recorded at install, the build is downloaded, checked,
unpacked beside the old one, its ffmpeg and ffprobe run, and only then do the saved paths move to
it. The branch in use is kept while BtbN builds it; once it is dropped (it then gets no more
fixes), the newest branch is taken. A failure leaves the old build in use, is recorded in
~/.tarjim/ffmpeg.json and is tried again the next day. The old build is removed at the next
check, so a job started just before the change still finds its files.
"""
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from tarjim import config, ffmpeg_release, ffmpeg_setup, update

CHECK_EVERY = 24 * 3600
OVERRIDES = ("TARJIM_FFMPEG", "TARJIM_FFPROBE")
AVAILABLE = sys.platform == "win32"


def record(state: str, name: str, detail: str = "") -> None:
    config.HOME.mkdir(parents=True, exist_ok=True)
    (config.HOME / "ffmpeg.json").write_text(json.dumps(
        {"state": state, "build": name, "detail": detail, "at": time.time()}), encoding="utf-8")


def progress() -> dict[str, Any]:
    try:
        return dict(json.loads((config.HOME / "ffmpeg.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return {}


def own() -> Path | None:
    """The build in use when both saved paths are tarjim's own and nothing overrides them."""
    if any(os.environ.get(name) for name in OVERRIDES):
        return None
    saved = config.settings()
    folders = {ffmpeg_release.folder_of(saved.get(name, "")) for name in ("ffmpeg", "ffprobe")}
    folder = folders.pop() if len(folders) == 1 else None
    return folder if folder and Path(saved["ffmpeg"]).is_file() else None


def allowed(idle: bool) -> bool:
    return idle and AVAILABLE and update.automatic() and update.installed_by_uv()


def due(now: float) -> bool:
    return now - float(config.setting("ffmpeg_checked") or 0) >= CHECK_EVERY


def renew(folder: Path) -> str:
    """A newer build of the branch in use, or the old one as it was; gives the build's name."""
    have, name = ffmpeg_release.installed(folder)
    listed = ffmpeg_release.ask()
    found = ffmpeg_release.choose(listed, name or ffmpeg_setup.ARCHIVE)
    if not found:
        return ""
    config.save("ffmpeg_latest", f"{listed[found]}  {found}")
    if found == name and hmac.compare_digest(listed[found], have):
        return ""
    try:
        ffmpeg_setup.use(ffmpeg_release.build(found, listed[found]))
    except ffmpeg_release.FAILURES as error:
        record("failed", found, str(error))
        return ""
    record("done", found)
    return found


def refresh(idle: bool, now: float | None = None) -> str:
    """Called by the update watch; gives the build now in use when it changed. Builds no longer
    in use go first, whenever nothing runs, even with automatic updates off: an install from the
    page leaves the one it replaced, as a job may have been using it."""
    now = time.time() if now is None else now
    folder = own()
    if folder is None or not idle or not ffmpeg_setup.PLACING.acquire(blocking=False):
        return ""
    try:
        ffmpeg_release.tidy({folder})
        if not allowed(idle) or not due(now):
            return ""
        config.save("ffmpeg_checked", str(now))
        return renew(folder)
    finally:
        ffmpeg_setup.PLACING.release()


def view() -> dict[str, Any]:
    folder = own()
    if folder is None:
        return {"own": False}
    have, name = ffmpeg_release.installed(folder)
    state = progress()
    return {"own": True, "build": name, "sha256": have, "latest": config.setting("ffmpeg_latest"),
            "state": state.get("state", ""), "detail": state.get("detail", "")}
