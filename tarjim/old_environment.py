"""The environment a clone left behind when it moved onto another Python (source_updater.py
renames it to ".venv-3.11" and makes a new one), removed once nothing runs from it."""
import shutil
import sys
from pathlib import Path

from tarjim import update


def locked(program: Path) -> bool:
    """Windows keeps a program's file locked while it runs."""
    try:
        with program.open("r+b"):
            return False
    except FileNotFoundError:
        return False
    except OSError:
        return True


def in_use(kept: Path) -> bool:
    """A program still runs from the old environment: a chat connection Claude started before
    the move goes on with the old libraries, and loads some only when first needed (keyring, for
    the engine's token), so they stay until it ends. Elsewhere a running program's files can be
    deleted, so its mapped files are looked at instead."""
    if sys.platform == "win32":
        return any(locked(kept / "Scripts" / name) for name in ("python.exe", "pythonw.exe"))
    import psutil

    for process in psutil.process_iter():
        try:
            if any(str(kept) in found.path for found in process.memory_maps()):
                return True
        except psutil.Error:
            continue
    return False


def forget_old_environment() -> None:
    """A clone moved onto another Python kept its old environment beside the new one
    (".venv-3.11"); once the engine runs on the new one and nothing runs from the old one, it
    goes. A start while something still does leaves it for a later start."""
    here = Path(sys.prefix)
    if not update.from_source() or not (here / "pyvenv.cfg").is_file():
        return
    for kept in here.parent.glob(f"{here.name}-3.*"):
        ours = (kept / "pyvenv.cfg").is_file() or (kept / "Scripts").is_dir()
        if kept.name != f"{here.name}-{update.running_minor()}" and ours and not in_use(kept):
            shutil.rmtree(kept, ignore_errors=True)
