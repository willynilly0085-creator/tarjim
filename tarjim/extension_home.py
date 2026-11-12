"""Keep the browser extension in one short folder that never moves, so the person loads it once.

The copy inside the installed package lives deep in a Python folder that changes with every
update or Python version. The browser keeps pointing at the same folder, and each update of tarjim
refreshes the files there; the browser picks them up on its next start or on "Reload".

Firefox reads the same files with a manifest of its own (2026-11-12): its background is a page's
script, not a service worker, and an add-on there names itself. That copy is a second folder.
"""
import json
import shutil
from pathlib import Path
from typing import Any

from tarjim import config

PACKAGED = Path(__file__).resolve().parent / "extension"
MANIFEST = "manifest.json"
GECKO_ID = "tarjim@indicators.sa"  # the name Firefox knows the add-on by (native_setup.py too)
FIREFOX_SINCE = "128.0"  # module scripts in the background, and its permissions granted at install


def signature(folder: Path) -> set[tuple[str, int, int]]:
    """Copies keep file times, so a matching list of names, sizes and times means the same files."""
    return {(str(f.relative_to(folder)), f.stat().st_size, int(f.stat().st_mtime))
            for f in folder.rglob("*") if f.is_file()}


def current(folder: Path) -> bool:
    return (folder / MANIFEST).is_file() and signature(folder) == signature(PACKAGED)


def extension_folder() -> str:
    """The folder to load in the browser, refreshed from the package when tarjim was updated."""
    if not (PACKAGED / MANIFEST).is_file():
        return ""
    folder = config.HOME / "extension"
    if folder.resolve() == PACKAGED:
        return str(folder)
    if not current(folder):
        try:
            shutil.rmtree(folder, ignore_errors=True)
            shutil.copytree(PACKAGED, folder)
        except OSError:
            return str(PACKAGED)
    return str(folder)


def for_firefox(manifest: dict[str, Any]) -> dict[str, Any]:
    """The manifest as Firefox reads it. The add-on sends nothing off this computer, which
    Mozilla asks every add-on to say."""
    made = dict(manifest)
    made["background"] = {"scripts": [manifest["background"]["service_worker"]],
                          "type": "module"}
    made["browser_specific_settings"] = {"gecko": {
        "id": GECKO_ID, "strict_min_version": FIREFOX_SINCE,
        "data_collection_permissions": {"required": ["none"]}}}
    return made


def firefox_manifest() -> str:
    packaged = json.loads((PACKAGED / MANIFEST).read_text(encoding="utf-8"))
    return json.dumps(for_firefox(packaged), ensure_ascii=False, indent=2) + "\n"


def same_but_manifest(folder: Path) -> bool:
    mine = {entry for entry in signature(folder) if entry[0] != MANIFEST}
    return mine == {entry for entry in signature(PACKAGED) if entry[0] != MANIFEST}


def firefox_folder() -> str:
    """The folder to load in Firefox, refreshed when tarjim was updated; "" when it cannot be
    made."""
    if not (PACKAGED / MANIFEST).is_file():
        return ""
    folder, wanted = config.HOME / "extension-firefox", firefox_manifest()
    kept = folder / MANIFEST
    fresh = kept.is_file() and kept.read_text(encoding="utf-8") == wanted
    if not (fresh and same_but_manifest(folder)):
        try:
            shutil.rmtree(folder, ignore_errors=True)
            shutil.copytree(PACKAGED, folder)
            kept.write_text(wanted, encoding="utf-8", newline="\n")
        except OSError:
            return ""
    return str(folder)
