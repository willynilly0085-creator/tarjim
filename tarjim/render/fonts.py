"""Whether a font the person chose is on this computer (2026-11-09).

The font's name goes into the subtitle file, and libass quietly draws another one when it is
not installed: Arabic in a font without Arabic letters is drawn as boxes. So a chosen font is
looked up among the installed ones before a subtitle is drawn, and one that is not there gives
way to the language's own font, with a line in the log. When the list cannot be read (another
system, a locked registry) the name is trusted, as it was before settings existed.
"""
import functools
import re
import subprocess
import sys

KEYS = (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",)
KIND = re.compile(r"\s*\((TrueType|OpenType|All res)\)\s*$", re.IGNORECASE)


def names_in(entries: list[str]) -> set[str]:
    """Each family named in the registry's entries: "Cambria & Cambria Math (TrueType)"."""
    return {name.strip().lower() for entry in entries for name in KIND.sub("", entry).split("&")
            if name.strip()}


def windows_entries() -> list[str]:
    import winreg

    found: list[str] = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, KEYS[0]) as key:
                found += [winreg.EnumValue(key, i)[0]
                          for i in range(winreg.QueryInfoKey(key)[1])]
        except OSError:
            continue
    return found


def fontconfig_entries() -> list[str]:
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True,
                         timeout=20, check=False)
    return [name for line in out.stdout.splitlines() for name in line.split(",")]


@functools.cache
def installed() -> frozenset[str] | None:
    """Every installed family, lower case; None when they cannot be listed."""
    try:
        entries = windows_entries() if sys.platform == "win32" else fontconfig_entries()
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return frozenset(names_in(entries)) or None


def present(name: str) -> bool:
    found, wanted = installed(), name.strip().lower()
    if found is None:
        return True
    return any(entry == wanted or entry.startswith(wanted + " ") for entry in found)


def usable(name: str, usual: str) -> str:
    """The chosen font when it is installed, else the language's own."""
    if name == usual or present(name):
        return name
    print(f"look: the font {name!r} is not on this computer; {usual!r} draws the subtitles",
          flush=True)
    return usual
