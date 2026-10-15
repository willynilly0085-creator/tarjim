"""The versions of tarjim's libraries that were tested with this release.

They ship inside the package (constraints.txt, written by scripts/pins.py) so the engine can
compare them with what is installed without asking anyone. yt-dlp keeps itself current, and the
PyTorch family follows the build uv picks for the graphics card, so neither is pinned.
"""
import re
from importlib import metadata
from pathlib import Path

FILE = Path(__file__).with_name("constraints.txt")
# sympy is here because some PyTorch builds ask for one exact sympy.
FLOATING = {"yt-dlp", "torch", "torchaudio", "torchvision", "torchcodec", "triton", "sympy"}
FLOATING_FAMILIES = ("nvidia-", "cuda-", "pytorch-triton")
PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9.+!_-]+)\s*(;.*)?")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def floating(name: str) -> bool:
    found = canonical(name)
    return found in FLOATING or found.startswith(FLOATING_FAMILIES)


def parse(text: str) -> dict[str, set[str]]:
    """Every pinned library with its versions (one per platform or Python, when they differ)."""
    found: dict[str, set[str]] = {}
    for line in text.splitlines():
        match = PIN.fullmatch(line.strip())
        if match:
            found.setdefault(canonical(match[1]), set()).add(match[2])
    return found


def shipped() -> dict[str, set[str]]:
    try:
        return parse(FILE.read_text(encoding="utf-8"))
    except OSError:
        return {}


def installed(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return ""


def drift(pinned: dict[str, set[str]] | None = None) -> list[str]:
    """Installed libraries at a version other than the tested one. One that is not installed is
    left out: its pin is for another platform."""
    pinned = shipped() if pinned is None else pinned
    return sorted(name for name, versions in pinned.items()
                  if installed(name) and installed(name) not in versions)
