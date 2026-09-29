"""Start tarjim's engine when the person signs in to their computer, without any window, so the
browser extension and chat tools find it after a restart. The person turns it on or off.

Windows: a small script in the Startup folder. macOS: a LaunchAgent. Linux: an autostart entry.
"""
import os
import sys
from pathlib import Path

STARTUP = Path("Microsoft") / "Windows" / "Start Menu" / "Programs" / "Startup"


def entry() -> Path:
    if sys.platform == "win32":
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return roaming / STARTUP / "tarjim.vbs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / "com.tarjim.server.plist"
    return Path.home() / ".config" / "autostart" / "tarjim.desktop"


def quiet_python() -> str:
    """pythonw on Windows runs without a console window."""
    windowless = Path(sys.executable).with_name("pythonw.exe")
    return str(windowless) if sys.platform == "win32" and windowless.exists() else sys.executable


def windows_script(python: str) -> str:
    if not python.lower().endswith("pythonw.exe"):
        python = str(Path(python).with_name("pythonw.exe"))
    return f'CreateObject("WScript.Shell").Run """{python}"" -m tarjim.server", 0, False\n'


def mac_agent(python: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict>'
            "<key>Label</key><string>com.tarjim.server</string>"
            f"<key>ProgramArguments</key><array><string>{python}</string><string>-m</string>"
            "<string>tarjim.server</string></array><key>RunAtLoad</key><true/></dict></plist>\n")


def linux_entry(python: str) -> str:
    return ("[Desktop Entry]\nType=Application\nName=tarjim\n"
            f"Exec={python} -m tarjim.server\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n")


def enabled() -> bool:
    return entry().is_file()


def enable() -> None:
    python = quiet_python()
    text = {"win32": windows_script, "darwin": mac_agent}.get(sys.platform, linux_entry)(python)
    entry().parent.mkdir(parents=True, exist_ok=True)
    entry().write_text(text, encoding="utf-8")


def disable() -> None:
    entry().unlink(missing_ok=True)
