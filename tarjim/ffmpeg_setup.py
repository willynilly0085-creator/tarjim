"""Install ffmpeg for people who do not have it: a checksum-verified LGPL build on Windows,
plain instructions elsewhere. ffmpeg_update keeps it current; ffmpeg_release does the checking.

ARCHIVE is the release branch tested with this release of tarjim. A fresh install takes it while
BtbN still builds it, and the newest branch once it is gone; a release of tarjim moves it on.
"""
import sys
import threading
from pathlib import Path

from tarjim import config, ffmpeg_release

ARCHIVE = "ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip"
ELSEWHERE = ("Install ffmpeg with your package manager: brew install ffmpeg (macOS) or "
             "sudo apt install ffmpeg (Linux)")
PLACING = threading.Lock()  # one install or update of tarjim's ffmpeg at a time


def use(binary: Path) -> None:
    """New programs start from this build; one already running keeps the files it has."""
    config.save("ffmpeg", str(binary))
    config.save("ffprobe", str(binary.with_name("ffprobe.exe")))
    config.prepare_environment()


def in_use() -> set[Path]:
    saved = config.settings()
    found = (ffmpeg_release.folder_of(saved.get(name, "")) for name in ("ffmpeg", "ffprobe"))
    return {folder for folder in found if folder}


def install_ffmpeg() -> Path:
    if sys.platform != "win32":
        raise RuntimeError(ELSEWHERE)
    with PLACING:
        listed = ffmpeg_release.ask()
        name = ffmpeg_release.choose(listed, ARCHIVE)
        if not name:
            raise RuntimeError("ffmpeg checksum is not published")
        binary = ffmpeg_release.build(name, listed[name])
        use(binary)
        ffmpeg_release.tidy(in_use())
    return binary
