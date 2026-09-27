"""Install ffmpeg for people who do not have it: a checksum-verified LGPL build on Windows,
plain instructions elsewhere."""
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from tarjim.config import HOME, prepare_environment, save

RELEASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
ARCHIVE = "ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip"
CHUNK = 1 << 20
ELSEWHERE = ("Install ffmpeg with your package manager: brew install ffmpeg (macOS) or "
             "sudo apt install ffmpeg (Linux)")


def published_digest(listing: str) -> str:
    for line in listing.splitlines():
        digest, _, name = line.strip().partition("  ")
        if name == ARCHIVE:
            return digest
    raise RuntimeError("ffmpeg checksum is not published")


def fetch_archive(target: Path) -> None:
    import requests

    wanted = published_digest(requests.get(RELEASE + "checksums.sha256", timeout=30).text)
    digest = hashlib.sha256()
    with (requests.get(RELEASE + ARCHIVE, stream=True, timeout=60) as reply,
          target.open("wb") as out):
        reply.raise_for_status()
        for chunk in reply.iter_content(CHUNK):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != wanted:
        raise RuntimeError("ffmpeg download does not match its published checksum")


def install_ffmpeg() -> Path:
    if sys.platform != "win32":
        raise RuntimeError(ELSEWHERE)
    folder = HOME / "tools" / "ffmpeg"
    with tempfile.TemporaryDirectory() as scratch:
        archive = Path(scratch) / ARCHIVE
        fetch_archive(archive)
        shutil.rmtree(folder, ignore_errors=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(folder)
    binary = next(folder.rglob("ffmpeg.exe"))
    save("ffmpeg", str(binary))
    save("ffprobe", str(binary.with_name("ffprobe.exe")))
    prepare_environment()
    return binary
