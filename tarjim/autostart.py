"""Start tarjim's engine when the person signs in to their computer, without any window, so the
browser extension and chat tools find it after a restart. The person turns it on or off.

Windows: a small script in the Startup folder. macOS: a LaunchAgent. Linux: an autostart entry.
"""
import contextlib
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from tarjim.config import HOME

STARTUP = Path("Microsoft") / "Windows" / "Start Menu" / "Programs" / "Startup"
WINDOWS = """Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
engine = {launch}
shell.Environment("PROCESS").Item("TARJIM_LOG_TO_FILE") = "1"
Start "starting the engine"
pause = 60000
Do
  WScript.Sleep pause
  pause = 300000
  If Not files.FileExists(WScript.ScriptFullName) Then Exit Do
  If Not Running() Then Start "the engine was not running; starting it again"
Loop

Sub Start(reason)
  Note reason
  On Error Resume Next
  shell.Run engine, 0, False
  If Err.Number <> 0 Then Note "could not start " & engine & ": " & Err.Description
End Sub

Function Running()
  On Error Resume Next
  Set found = GetObject("winmgmts:").ExecQuery("select ProcessId from Win32_Process where " & _
    "CommandLine like '%-m tarjim.server%' or CommandLine like '%tarjim-serve%'")
  Running = found.Count > 0
  If Err.Number <> 0 Then Running = True
End Function

Sub Note(text)
  On Error Resume Next
  Set trace = files.OpenTextFile("{log}", 8, True)
  trace.WriteLine Now & " sign-in launch: " & text
  trace.Close
End Sub
"""


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


def windowless(python: str) -> str:
    return python if python.lower().endswith("pythonw.exe") else str(
        Path(python).with_name("pythonw.exe"))


def launch(python: str) -> str:
    return f'"""{windowless(python)}"" -P -m tarjim.server"'


def windows_script(python: str) -> str:
    """Writes a dated line to server.log and starts the engine; then, while the person is signed
    in, starts it again whenever no engine is running (after a minute, then every five), so one
    that failed at sign-in or stopped later comes back. It ends when the script is removed.
    TARJIM_LOG_TO_FILE: a virtual environment's pythonw.exe may be a console launcher, whose
    hidden console swallowed everything the engine printed (boot.py)."""
    return WINDOWS.replace("{launch}", launch(python)).replace("{log}", str(HOME / "server.log"))


def starts_anything(script: str) -> bool:
    """False when the Python the script names is gone: tarjim's folder was moved or rebuilt."""
    found = re.search(r'engine = """(.+?)""', script)
    return found is not None and Path(found.group(1)).exists()


def refresh() -> None:
    """A Startup script written by an older version for this same Python becomes today's."""
    if sys.platform != "win32" or not enabled():
        return
    with contextlib.suppress(OSError):
        text, wanted = entry().read_text(encoding="utf-8"), windows_script(quiet_python())
        if text != wanted and (launch(quiet_python()) in text or not starts_anything(text)):
            entry().write_text(wanted, encoding="utf-8")


def mac_agent(python: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict>'
            "<key>Label</key><string>com.tarjim.server</string>"
            f"<key>ProgramArguments</key><array><string>{escape(python)}</string>"
            "<string>-P</string><string>-m</string>"
            "<string>tarjim.server</string></array><key>RunAtLoad</key><true/></dict></plist>\n")


def linux_entry(python: str) -> str:
    return ("[Desktop Entry]\nType=Application\nName=tarjim\n"
            f'Exec="{python}" -P -m tarjim.server\nNoDisplay=true\n'
            "X-GNOME-Autostart-enabled=true\n")


def enabled() -> bool:
    return entry().is_file()


def enable() -> None:
    python = quiet_python()
    text = {"win32": windows_script, "darwin": mac_agent}.get(sys.platform, linux_entry)(python)
    entry().parent.mkdir(parents=True, exist_ok=True)
    entry().write_text(text, encoding="utf-8")


def disable() -> None:
    entry().unlink(missing_ok=True)
