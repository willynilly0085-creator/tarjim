"""The installed fonts that can write a language (2026-11-09).

The page lists only these for "نوع الخط", and a font outside them is refused when it is saved:
libass quietly draws a font that lacks a script's letters as boxes. A font counts when it maps
every letter of the language's own name ("العربية", "日本語"). Each file is read once a run
(render/sfnt.py) and again only when it changes.
"""
import functools
import os
import sys
from pathlib import Path

from tarjim.languages import language
from tarjim.render.sfnt import Face, covers, read

SUFFIXES = {".ttf", ".otf", ".ttc"}


def folders() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = os.environ.get("LOCALAPPDATA", "")
        own = [Path(local) / "Microsoft" / "Windows" / "Fonts"] if local else []
        return [windows / "Fonts", *own]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
            home / ".local" / "share" / "fonts", home / ".fonts", Path("/System/Library/Fonts"),
            Path("/Library/Fonts"), home / "Library" / "Fonts"]


def files() -> list[Path]:
    return sorted(p for folder in folders() if folder.is_dir() for p in folder.rglob("*")
                  if p.suffix.lower() in SUFFIXES)


@functools.cache
def kept(path: str, _stamp: float) -> tuple[Face, ...]:
    return tuple(read(Path(path)))


def faces_of(path: Path) -> tuple[Face, ...]:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return ()
    return kept(str(path), stamp)


def letters(code: str) -> str:
    return "".join(sorted({c for c in language(code).native if c.isalpha()}))


def covering(code: str) -> list[str] | None:
    """Every family that writes this language, its usual font first; None when no font
    folder could be read (another system), so nothing is refused for it."""
    found = files()
    if not found:
        return None
    wanted = letters(code)
    names = {name for path in found for name, ranges in faces_of(path)
             if name and covers(ranges, wanted)}
    usual = language(code).font.lower()
    return sorted(names, key=lambda n: (n.lower() != usual, n.lower()))


def writes(name: str, code: str) -> list[str] | None:
    """None when this font can write the language (or the fonts cannot be listed), else the
    fonts that can."""
    found = covering(code)
    if found is None or name.strip().lower() in {f.lower() for f in found}:
        return None
    return found
