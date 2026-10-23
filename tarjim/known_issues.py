"""Published vulnerabilities in tarjim's libraries that the tested versions cannot avoid yet.

known_issues.json ships with each release (the same facts as SECURITY.md). Only the entries whose
affected versions include the version installed on this computer are shown, so an entry goes
away by itself once an update installs a fixed release. Nothing is asked of any server.
"""
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tarjim import pins

FILE = Path(__file__).with_name("known_issues.json")
SHOWN = ("id", "aliases", "package", "affected", "what", "reached", "reach", "tarjim", "fix")
DETAILS = ("https://github.com/willynilly0085-creator/tarjim/blob/master/SECURITY.md"
           "#known-library-issues")


def entries() -> list[dict[str, Any]]:
    try:
        found = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [entry for entry in found if isinstance(entry, dict)] if isinstance(found, list) else []


def affected(entry: dict[str, Any], version: str) -> bool:
    """An entry the engine cannot read is shown rather than hidden."""
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version

    try:
        return SpecifierSet(str(entry["affected"])).contains(Version(version), prereleases=True)
    except (InvalidSpecifier, InvalidVersion, KeyError):
        return True


def current(installed: Callable[[str], str] | None = None) -> list[dict[str, Any]]:
    """The entries that apply here, each with the version installed."""
    installed = installed or pins.installed  # looked up now, so a test can stand in for it
    shown = []
    for entry in entries():
        version = installed(str(entry.get("package", "")))
        if version and affected(entry, version):
            shown.append({**{key: entry.get(key) for key in SHOWN}, "installed": version})
    return shown


def view() -> dict[str, Any]:
    """For the page, /update and the chat tools."""
    return {"known_issues": current(), "known_issues_details": DETAILS}
