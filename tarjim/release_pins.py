"""The tested versions of tarjim's libraries for one release, fetched for the installer.

Standard library only, like the installer: a copy of this file sits beside the installer's copy
in ~/.tarjim while an update replaces the engine's folder. The files come only from the release
being installed (GitHub, over HTTPS, for its tag; or beside a local copy) and are used only when
every line is an exact version, so they cannot point uv at another index or file.
constraints.txt holds every tested version; overrides.txt the few that replace another
package's exact pin (a release older than that file has none, and installs without it).
python.txt names the Python the release runs on (a release older than that file runs on 3.11).
"""
import re
import urllib.request
from pathlib import Path
from typing import NamedTuple

REPO = "willynilly0085-creator/tarjim"
RELEASE = re.compile(rf"https://github\.com/{REPO}/archive/refs/tags/(v?\d+\.\d+\.\d+)\.zip")
RAW = f"https://raw.githubusercontent.com/{REPO}/{{tag}}/tarjim/{{name}}"
PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9.+!_-]+( *;[ -~]*)?")
CONSTRAINTS = "constraints.txt"
OVERRIDES = "overrides.txt"
PYTHON = "python.txt"
EARLIER_PYTHON = "3.11"
MINOR = re.compile(r"3\.\d{1,2}")
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
        listed = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
        why = "holds more than exact versions" if listed else "lists nothing"
        note(home, f"{name} {why}; installing without it")
        return None
    saved = home / name
    saved.write_text(text, encoding="utf-8")
    return saved


def python_for(source: str, home: Path) -> str:
    """The Python this release runs on, such as "3.12"; 3.11 when the release does not say."""
    try:
        with urllib.request.urlopen(pins_address(source, PYTHON), timeout=WAIT) as reply:
            text = reply.read(64).decode("utf-8").strip()
    except (OSError, ValueError, UnicodeDecodeError):
        return EARLIER_PYTHON
    if MINOR.fullmatch(text):
        return str(text)
    note(home, f"{PYTHON} says {text[:20]!r}; installing on Python {EARLIER_PYTHON}")
    return EARLIER_PYTHON


class Tested(NamedTuple):
    """What the release brings for its install: its tested versions, the overrides, its Python."""
    pins: Path | None = None
    lifted: Path | None = None
    python: str = EARLIER_PYTHON


NOTHING = Tested()


def install_command(uv: str, source: str, tested: Tested = NOTHING) -> list[str]:
    """uv picks the PyTorch build for the graphics card it finds (CPU when there is none). With
    the release's tested versions every other library moves to them, and yt-dlp and the PyTorch
    family to their newest; without them, uv takes the newest of each, as it did before.
    Overrides (only with them) lift another package's exact pin to a tested, safer release. The
    Python is the release's own (python.txt), so an update can move it to a newer one."""
    pinned = ["--upgrade", "-c", str(tested.pins)] if tested.pins else []
    pinned += ["--overrides", str(tested.lifted)] if tested.pins and tested.lifted else []
    return [uv, "tool", "install", "--force", "--python", tested.python, "--torch-backend",
            "auto", *pinned, f"tarjim[dub] @ {source}"]
