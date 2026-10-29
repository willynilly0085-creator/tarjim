"""Register the program the browser may run to start a stopped engine (native_host.py).

A browser runs such a program only for the extensions its manifest names. tarjim names the
extensions that reached the engine with its key, which happens only after the person pressed
Allow for them (pairing.py); a loaded-unpacked extension's id comes from its folder, so it is
learned from the requests rather than fixed here. The manifest and a small launcher live in
tarjim's home; Chrome and Edge find the manifest through the registry on Windows, and in a folder
of their own on macOS and Linux. Written again at every engine start, so a moved tarjim folder or
a new Python is picked up.
"""
import contextlib
import json
import sys
import threading
from pathlib import Path

from tarjim.config import HOME, save, setting

NAME = "sa.tarjim.wake"
REGISTRY = ("Google\\Chrome", "Microsoft\\Edge", "Chromium", "BraveSoftware\\Brave-Browser")
MAC = ("Google/Chrome", "Microsoft Edge", "Chromium", "BraveSoftware/Brave-Browser")
LINUX = ("google-chrome", "microsoft-edge", "chromium", "BraveSoftware/Brave-Browser")
KNOWN: set[str] = set()
SAVING = threading.Lock()


def origins() -> list[str]:
    try:
        found = json.loads(setting("extension_origins") or "[]")
    except ValueError:
        return []
    return sorted(o for o in found if isinstance(o, str) and o.startswith("chrome-extension://"))


def launcher(folder: Path) -> Path:
    """python.exe, not pythonw: the browser talks to the program through its standard streams."""
    python = Path(sys.executable)
    if sys.platform == "win32":
        path = folder / "wake.bat"
        console = python.with_name("python.exe")
        path.write_text(f'@"{console}" -P -m tarjim.native_host\r\n', encoding="utf-8")
        return path
    path = folder / "wake.sh"
    path.write_text(f'#!/bin/sh\nexec "{python}" -P -m tarjim.native_host\n', encoding="utf-8")
    path.chmod(0o755)
    return path


def manifest(folder: Path, allowed: list[str]) -> Path:
    path = folder / f"{NAME}.json"
    path.write_text(json.dumps({
        "name": NAME, "description": "tarjim: start the engine", "path": str(launcher(folder)),
        "type": "stdio", "allowed_origins": [f"{o.rstrip('/')}/" for o in allowed]}, indent=1),
        encoding="utf-8")
    return path


def point_browsers(path: Path) -> None:
    if sys.platform == "win32":
        import winreg

        for browser in REGISTRY:
            key = f"Software\\{browser}\\NativeMessagingHosts\\{NAME}"
            with contextlib.suppress(OSError), winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, str(path))
        return
    base = (Path.home() / "Library" / "Application Support", MAC) if sys.platform == "darwin" \
        else (Path.home() / ".config", LINUX)
    for browser in base[1]:
        folder = base[0] / browser / "NativeMessagingHosts"
        if folder.parent.is_dir():  # only browsers that are installed
            folder.mkdir(exist_ok=True)
            (folder / f"{NAME}.json").write_text(path.read_text(encoding="utf-8"), "utf-8")


def register() -> None:
    allowed = origins()
    if not allowed:
        return
    folder = HOME / "native"
    with contextlib.suppress(OSError):
        folder.mkdir(parents=True, exist_ok=True)
        point_browsers(manifest(folder, allowed))


def remember(origin: str) -> None:
    """An extension that reached the engine with its key may start it later. Cheap when known."""
    if origin in KNOWN or not origin.startswith("chrome-extension://"):
        return
    with SAVING:
        KNOWN.update(origins())
        if origin not in KNOWN:
            KNOWN.add(origin)
            save("extension_origins", json.dumps(sorted(KNOWN)))
            register()
