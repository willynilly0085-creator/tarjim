"""Where finished files go: an existing folder of this computer that tarjim may write in
(2026-11-09). A drive's root, the home folder, the Downloads folder itself and tarjim's own
folder are refused: tarjim clears and renames files in the folder it writes to. So are the
system's own folders, and the gate writes a trial file to know the folder takes one: on
Windows os.access only reads the read-only flag and passes the system folder itself."""
import os
import tempfile
from pathlib import Path
from typing import Any

from tarjim.prefs.spec import Refusal, Spec, Value, refuse

LONGEST = 240
OWN_FOLDER = "اختر مجلد داخلي خاص بالملفات، مو جذر القرص ولا مجلد المستخدم ولا مجلدات النظام"
SYSTEM = ("WINDIR", "SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")


def default_folder() -> str:
    return str(Path.home() / "Downloads" / "tarjim")


def system_folders() -> list[Path]:
    return [Path(os.environ[name]).resolve() for name in SYSTEM if os.environ.get(name)]


def inside(place: Path, roots: list[Path]) -> bool:
    return any(place == root or root in place.parents for root in roots)


def kept_away(place: Path) -> bool:
    from tarjim import config

    home = Path.home().resolve()
    return (place.parent == place or place in (home, home / "Downloads")
            or inside(place, [Path(config.HOME).resolve(), *system_folders()]))


def writable(place: Path) -> bool:
    """A trial file is made and removed (2026-11-09): the only check Windows answers truly."""
    try:
        handle, name = tempfile.mkstemp(dir=place, prefix=".tarjim-")
        os.close(handle)
        os.unlink(name)
    except OSError:
        return False
    return True


def folder(spec: Spec, raw: Any) -> Value | Refusal:
    text = str(raw).strip() if isinstance(raw, str) else ""
    works = default_folder()
    if not text or len(text) > LONGEST or "\0" in text or text.startswith(("\\\\", "//")):
        return refuse(spec, "يبي مسار مجلد على هالجهاز", works)
    place = Path(os.path.expandvars(text)).expanduser()
    if not place.is_absolute():
        return refuse(spec, "يبي المسار كامل، مثل C:\\Users\\اسمك\\Videos", works)
    place = place.resolve()
    if place == Path(works).resolve():
        return works  # tarjim's own folder: made when the first file is written
    if kept_away(place):
        return refuse(spec, OWN_FOLDER, works)
    if not place.is_dir() or not writable(place):
        return refuse(spec, "المجلد ما هو موجود أو ما نقدر نكتب فيه", works)
    return str(place)
