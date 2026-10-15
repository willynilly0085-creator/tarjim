"""The tested versions of tarjim's libraries for one release, fetched for the installer.

Standard library only, like the installer: a copy of this file sits beside the installer's copy
in ~/.tarjim while an update replaces the engine's folder. The files come only from the release
being installed (GitHub, over HTTPS, for its tag; or beside a local copy) and are used only when
every line is an exact version, so they cannot point uv at another index or file.
constraints.txt holds every tested version; overrides.txt the few that replace another
package's exact pin (a release older than that file has none, and installs without it).
"""
import re
import urllib.request
from pathlib import Path

REPO = "willynilly0085-creator/tarjim"
RELEASE = re.compile(rf"https://github\.com/{REPO}/archive/refs/tags/(v?\d+\.\d+\.\d+)\.zip")
RAW = f"https://raw.githubusercontent.com/{REPO}/{{tag}}/tarjim/{{name}}"
PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9.+!_-]+( *;[ -~]*)?")
CONSTRAINTS = "constraints.txt"
OVERRIDES = "overrides.txt"
MOST = 1 << 20
WAIT = 60


def pins_address(source: str, name: str = CONSTRAINTS) -> str:
    """The same release's file: from GitHub for its archive, or beside a local copy."""
    release = RELEASE.fullmatch(source)
    if release:
        return RAW.format(tag=release[1], name=name)
    if source.startswith("file:"):
        return f"{source.rstrip('/')}/tarjim/{name}"
    return "" if "://" in source else f"{Path(source).resolve().as_uri()}/tarjim/{name}"


def note(home: Path, text: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    with (home / "install.log").open("a", encoding="utf-8") as out:
        out.write(f"tarjim: {text}\n")


def plain_pins(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines()]
    pinned = [line for line in lines if line and not line.startswith("#")]
    return bool(pinned) and all(PIN.fullmatch(line) for line in pinned)


def tested_versions(source: str, home: Path, name: str = CONSTRAINTS) -> Path | None:
    """The release's file saved for uv, or nothing (noted in the install log)."""
    try:
        with urllib.request.urlopen(pins_address(source, name), timeout=WAIT) as reply:
            text = reply.read(MOST).decode("utf-8")
    except (OSError, ValueError) as error:
        note(home, f"{name} unavailable ({error}); installing without it")
        return None
    if not plain_pins(text):
        note(home, f"{name} holds more than exact versions; installing without it")
        return None
    saved = home / name
    saved.write_text(text, encoding="utf-8")
    return saved
