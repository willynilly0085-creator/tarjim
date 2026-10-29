"""ffmpeg builds from BtbN/FFmpeg-Builds, checked before tarjim uses one (Windows only).

The "latest" release is rebuilt every day and publishes checksums.sha256 beside its files. tarjim
follows a release branch, never master: the LGPL shared build named
ffmpeg-n<major>.<minor>-latest-win64-lgpl-shared-<major>.<minor>.zip. A name goes into an address
only when it is exactly that, and a digest only when it is 64 hex characters; the zip is refused
unless its SHA-256 is the one listed for its exact name. Each build is unpacked into its own folder
under ~/.tarjim/tools/ffmpeg, named by its digest, beside the one in use, with build.sha256 in it
saying what it is; the saved ffmpeg and ffprobe paths then move to it. A build no setting points
to is removed later, while nothing runs (tidy), so a running ffmpeg keeps its files.
"""
import hashlib
import hmac
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from tarjim import config
from tarjim.installer import NO_WINDOW

RELEASE = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
NAME = re.compile(r"ffmpeg-n([0-9]{1,3})\.([0-9]{1,3})-latest-win64-lgpl-shared-\1\.\2\.zip")
DIGEST = re.compile(r"[0-9a-f]{64}")
RECORD = "build.sha256"
WAIT = (15, 120)
CHUNK = 1 << 20
RUN_SECONDS = 30
PAIR = 2  # a digest and a name


class Refused(RuntimeError):
    """What came from the release cannot be used."""


FAILURES = (OSError, RuntimeError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError)


def root() -> Path:
    return config.HOME / "tools" / "ffmpeg"


def branch(name: str) -> tuple[int, ...]:
    match = NAME.fullmatch(name)
    return (int(match[1]), int(match[2])) if match else ()


def builds(listing: str) -> dict[str, str]:
    """Every release-branch build in checksums.sha256, by name, with its digest."""
    found = {}
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) == PAIR and DIGEST.fullmatch(parts[0]) and branch(parts[1]):
            found[parts[1]] = parts[0]
    return found


def choose(listed: dict[str, str], wanted: str) -> str:
    """The branch asked for while it is still built; when it is gone, the newest branch."""
    if wanted in listed:
        return wanted
    return max(listed, key=branch, default="")


def ask() -> dict[str, str]:
    """The listing, or nothing when GitHub cannot be reached."""
    import requests

    try:
        reply = requests.get(RELEASE + "checksums.sha256", timeout=WAIT)
        reply.raise_for_status()
    except requests.RequestException:
        return {}
    return builds(reply.text)


def download(name: str, digest: str, target: Path) -> None:
    import requests

    if not branch(name) or not DIGEST.fullmatch(digest):
        raise Refused(f"not an ffmpeg build tarjim uses: {name!r}")
    found = hashlib.sha256()
    with requests.get(RELEASE + name, stream=True, timeout=WAIT) as reply, target.open("wb") as out:
        reply.raise_for_status()
        for chunk in reply.iter_content(CHUNK):
            found.update(chunk)
            out.write(chunk)
    if not hmac.compare_digest(found.hexdigest(), digest):
        target.unlink(missing_ok=True)
        raise Refused(f"{name} does not match its published checksum")


def runs(program: Path) -> bool:
    try:
        done = subprocess.run([str(program), "-version"], capture_output=True, timeout=RUN_SECONDS,
                              creationflags=NO_WINDOW, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def unpack(archive: Path, folder: Path) -> Path:
    """The checked zip unpacked; its ffmpeg.exe, refused unless it and ffprobe.exe run."""
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(folder)
    binary = next(folder.rglob("ffmpeg.exe"), None)
    if binary is None or not all(map(runs, (binary, binary.with_name("ffprobe.exe")))):
        raise Refused(f"{archive.name} has no ffmpeg.exe and ffprobe.exe that run")
    return binary


def place(archive: Path, digest: str) -> Path:
    files = archive.with_name("files")
    binary = unpack(archive, files)
    (files / RECORD).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    target = root() / digest[:16]
    shutil.rmtree(target, ignore_errors=True)
    files.rename(target)
    return target / binary.relative_to(files)


def in_place(digest: str) -> Path | None:
    """The ffmpeg.exe of this very build when it is already unpacked and runs. Unpacking it again
    would first remove the folder a running job may be using."""
    folder = root() / digest[:16]
    if installed(folder)[0] != digest:
        return None
    binary = next(folder.rglob("ffmpeg.exe"), None)
    usable = binary and all(map(runs, (binary, binary.with_name("ffprobe.exe"))))
    return binary if usable else None


def build(name: str, digest: str) -> Path:
    """Download, check and unpack a build beside the one in use; gives its ffmpeg.exe."""
    present = in_place(digest)
    if present:
        return present
    staging = root() / ".new"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        archive = staging / name
        download(name, digest, archive)
        return place(archive, digest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def folder_of(program: str) -> Path | None:
    """The build folder a saved path lies in, when it is one of tarjim's."""
    if not program:
        return None
    try:
        inside = Path(program).resolve().relative_to(root().resolve())
    except (OSError, ValueError):
        return None
    return root() / inside.parts[0] if len(inside.parts) > 1 else None


def installed(build_folder: Path) -> tuple[str, str]:
    """The digest and name build.sha256 gives; a build from before it was kept gives none."""
    try:
        parts = (build_folder / RECORD).read_text(encoding="utf-8").split()
    except OSError:
        return "", ""
    usable = len(parts) == PAIR and DIGEST.fullmatch(parts[0]) and branch(parts[1])
    return (parts[0], parts[1]) if usable else ("", "")


def tidy(keep: set[Path]) -> None:
    """Builds no saved path points to; a file still open stays until the next time."""
    if not root().is_dir():
        return
    for found in root().iterdir():
        if found not in keep:
            shutil.rmtree(found, ignore_errors=True)
