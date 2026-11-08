"""Where finished files go: an existing folder of this computer that tarjim may write in
(2026-11-09). A drive's root, the home folder, the Downloads folder itself and tarjim's own
folder are refused: tarjim clears and renames files in the folder it writes to."""
import os
from pathlib import Path
from typing import Any

from tarjim.prefs.spec import Refusal, Spec, Value, refuse

LONGEST = 240


def default_folder() -> str:
    return str(Path.home() / "Downloads" / "tarjim")


def kept_away(place: Path) -> bool:
    from tarjim import config

    home = Path.home().resolve()
    own = Path(config.HOME).resolve()
    return (place.parent == place or place in (home, home / "Downloads")
            or place == own or own in place.parents)


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
        return refuse(spec, "اختر مجلد داخلي خاص بالملفات، مو جذر القرص ولا مجلد المستخدم", works)
    if not place.is_dir() or not os.access(place, os.W_OK):
        return refuse(spec, "المجلد ما هو موجود أو ما نقدر نكتب فيه", works)
    return str(place)
