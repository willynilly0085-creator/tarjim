"""Node.js releases from nodejs.org, checked before tarjim uses one.

index.json lists every release, newest first; tarjim takes the newest LTS that has a Windows zip.
Each release publishes SHASUMS256.txt beside its files, and the zip is refused unless its SHA-256
is the one written there for its exact name. Both come over HTTPS. A version goes into an address
or a command only when it is exactly v<major>.<minor>.<patch>. A new Node.js is unpacked beside
the one in use, the programs are installed into it, and only then does it take the old one's
place (own_node.swap), so a failure at any step leaves the person's programs working as before.
"""
import hashlib
import hmac
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from tarjim.engines import own_node
from tarjim.installer import NO_WINDOW

DIST = "https://nodejs.org/dist"
VERSION = re.compile(r"v([0-9]{1,4})\.([0-9]{1,4})\.([0-9]{1,4})")
DIGEST = re.compile(r"[0-9a-f]{64}")
WAIT = (15, 120)
CHUNK = 1 << 20
NPM_SECONDS = 900


class Refused(ValueError):
    """What came from nodejs.org, or from npm, cannot be used."""


FAILURES = (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError)


def number(version: object) -> tuple[int, ...]:
    match = VERSION.fullmatch(version) if isinstance(version, str) else None
    return tuple(int(part) for part in match.groups()) if match else ()


def newer(found: str, have: str) -> bool:
    return bool(number(found)) and bool(number(have)) and number(found) > number(have)


def zip_name(version: str) -> str:
    if not number(version):
        raise ValueError(f"not a Node.js version: {version!r}")
    return f"node-{version}-win-x64.zip"


def windows_lts(entry: object) -> str:
    """The entry's version when it is an LTS release with a Windows zip, otherwise nothing."""
    if not isinstance(entry, dict) or not entry.get("lts"):
        return ""
    files, version = entry.get("files"), entry.get("version")
    usable = isinstance(files, list) and "win-x64-zip" in files and bool(number(version))
    return str(version) if usable else ""


def newest_lts(index: object) -> str:
    releases = index if isinstance(index, list) else []
    return next((found for found in map(windows_lts, releases) if found), "")


def fetch_text(url: str) -> str:
    import requests

    reply = requests.get(url, timeout=WAIT)
    reply.raise_for_status()
    return str(reply.text)


def ask_index() -> Any:
    """index.json, or nothing when nodejs.org cannot be reached or does not answer in JSON."""
    import json

    try:
        return json.loads(fetch_text(f"{DIST}/index.json"))
    except (OSError, ValueError):
        return []


def save(url: str, target: Path) -> None:
    import requests

    with requests.get(url, timeout=WAIT, stream=True) as reply:
        reply.raise_for_status()
        with target.open("wb") as file:
            for chunk in reply.iter_content(CHUNK):
                file.write(chunk)


def published(sums: str, name: str) -> str:
    """The SHA-256 that SHASUMS256.txt gives for exactly this file name."""
    for line in sums.splitlines():
        parts = line.split()
        if parts[1:] == [name] and DIGEST.fullmatch(parts[0]):
            return parts[0]
    return ""


def digest(path: Path) -> str:
    found = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK), b""):
            found.update(chunk)
    return found.hexdigest()


def verify(path: Path, sums: str) -> None:
    expected = published(sums, path.name)
    if not expected:
        raise Refused(f"SHASUMS256.txt does not list {path.name}")
    if not hmac.compare_digest(digest(path), expected):
        raise Refused(f"{path.name} does not match SHASUMS256.txt")


def download(version: str, folder: Path) -> Path:
    name = zip_name(version)
    sums = fetch_text(f"{DIST}/{version}/SHASUMS256.txt")
    target = folder / name
    save(f"{DIST}/{version}/{name}", target)
    try:
        verify(target, sums)
    except Refused:
        target.unlink(missing_ok=True)
        raise
    return target


def unpack(archive: Path, folder: Path) -> Path:
    """The checked zip, unpacked beside the Node.js in use."""
    with zipfile.ZipFile(archive) as opened:
        opened.extractall(folder)
    unpacked = folder / archive.name.removesuffix(".zip")
    if not (unpacked / "node.exe").is_file() or not (unpacked / "npm.cmd").is_file():
        raise Refused(f"{archive.name} has no node.exe and npm.cmd")
    return unpacked


def add(folder: Path, packages: list[str]) -> None:
    """The programs the old Node.js had, installed into the new one before it is used."""
    if not packages:
        return
    command = [str(folder / "npm.cmd"), "install", "-g", "--prefix", str(folder),
               own_node.scripts_for(packages), *(f"{package}@latest" for package in packages)]
    done = subprocess.run(command, capture_output=True, text=True, timeout=NPM_SECONDS,
                          env=own_node.environment(folder), creationflags=NO_WINDOW, check=False)
    if done.returncode:
        raise Refused((done.stderr.strip().splitlines() or ["npm failed"])[-1])


def build(version: str, packages: list[str]) -> None:
    """Download, check, unpack and fill a Node.js beside the old one, then swap it in."""
    staging = own_node.staging()
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        unpacked = unpack(download(version, staging), staging)
        add(unpacked, packages)
        own_node.swap(unpacked)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
