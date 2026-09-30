"""Keep the browser extension in one short folder that never moves, so the person loads it once.

The copy inside the installed package lives deep in a Python folder that changes with every
update or Python version. The browser keeps pointing at the same folder, and each update of tarjim
refreshes the files there; the browser picks them up on its next start or on "Reload".
"""
import shutil
from pathlib import Path

from tarjim import config

PACKAGED = Path(__file__).resolve().parent / "extension"
MANIFEST = "manifest.json"


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
