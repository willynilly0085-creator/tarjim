"""Where the models go when the usual place cannot be written.

Models are kept in the shared cache every AI tool uses (`~/.cache/huggingface`), so one already
downloaded is not downloaded twice. On some computers that folder belongs to another account (it
was made by a program run as administrator) and every download ends in "Access is denied". tarjim
then keeps its models in its own folder, and remembers that choice.
"""
import os
import tempfile
from pathlib import Path


def writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            return True
    except OSError:
        return False


def usual() -> Path:
    return Path.home() / ".cache" / "huggingface"


def fallback(chosen: str, own: Path) -> str:
    """The folder to remember, or nothing when the person chose one or the usual one works."""
    if chosen or os.environ.get("HF_HOME") or writable(usual()):
        return ""
    return str(own)
