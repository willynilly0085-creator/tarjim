"""The tarjim shortcut on the desktop and in the Start menu, which runs `tarjim.wake`: it starts
the engine when it is not running and then opens its page, so anyone can bring back a stopped
engine with a double-click.

Older installers put a plain link to the page on the desktop (tarjim.url), which opened a page
that could not load once the engine had stopped. The engine replaces that link with the shortcut
when it starts; a link it did not write is left alone. Windows only: elsewhere tarjim is
installed through a chat app, which starts the engine itself.
"""
import base64
import os
import subprocess
import sys
from pathlib import Path

from tarjim.autostart import quiet_python

NAME = "tarjim.lnk"
OLD = "tarjim.url"
ICON = Path(__file__).with_name("web") / "tarjim.ico"
PROGRAMS = Path("Microsoft") / "Windows" / "Start Menu" / "Programs"
FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
NO_WINDOW = 0x08000000


def desktop() -> Path:
    """The desktop the person sees, also when OneDrive or a policy moved it."""
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, FOLDERS) as key:
        return Path(os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0]))


def start_menu() -> Path:
    return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / PROGRAMS


def quoted(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def script(places: list[Path], python: str) -> str:
    lines = ["$shell = New-Object -ComObject WScript.Shell"]
    for place in places:
        lines += [f"$link = $shell.CreateShortcut({quoted(str(place))})",
                  f"$link.TargetPath = {quoted(python)}",
                  "$link.Arguments = '-P -m tarjim.wake'",
                  f"$link.WorkingDirectory = {quoted(str(Path.home()))}",
                  f"$link.IconLocation = {quoted(f'{ICON},0')}",
                  "$link.Description = 'tarjim'", "$link.Save()"]
    return "\n".join(lines)


def ours(link: Path) -> bool:
    try:
        text = link.read_text(encoding="ascii", errors="replace")
    except OSError:
        return False
    return "[InternetShortcut]" in text and "URL=http://127.0.0.1:" in text


def make(python: str = "") -> list[Path]:
    """Both shortcuts written, and the old link to the page removed. The ones written."""
    if sys.platform != "win32":
        return []
    places = [desktop() / NAME, start_menu() / NAME]
    for place in places:
        place.parent.mkdir(parents=True, exist_ok=True)
    encoded = base64.b64encode(script(places, python or quiet_python()).encode("utf-16-le"))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                    encoded.decode()], capture_output=True, timeout=60, check=False,
                   creationflags=NO_WINDOW)
    if ours(desktop() / OLD) and (desktop() / NAME).is_file():
        (desktop() / OLD).unlink(missing_ok=True)
    return [place for place in places if place.is_file()]


def upgrade() -> bool:
    """Replace the old link to the page, once, when an older installer left one."""
    if sys.platform != "win32":
        return False
    try:
        return ours(desktop() / OLD) and bool(make())
    except (OSError, subprocess.SubprocessError):
        return False
