"""Install the tarjim engine for someone who only has the chat plugin, then start it.

Runs as its own hidden background process (standard library only) and records its progress in
~/.tarjim/install.json so the chat tools can report it.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
STATE = HOME / "install.json"
LOG = HOME / "install.log"
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
DETACHED = 0x00000008 if sys.platform == "win32" else 0
BREAKAWAY = 0x01000000 if sys.platform == "win32" else 0
STILL_ACTIVE = 259


def record(state: str, detail: str = "") -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"state": state, "detail": detail, "at": time.time(),
                                 "pid": os.getpid()}), encoding="utf-8")


def alive(pid: int) -> bool:
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes

    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(handle)
    return code.value == STILL_ACTIVE


def install_command(uv: str, source: str) -> list[str]:
    """uv picks the PyTorch build for the graphics card it finds (CPU when there is none)."""
    return [uv, "tool", "install", "--force", "--python", "3.11", "--torch-backend", "auto",
            f"tarjim[dub] @ {source}"]


def tool_bin(uv: str) -> Path:
    out = subprocess.run([uv, "tool", "dir", "--bin"], capture_output=True, text=True,
                         creationflags=NO_WINDOW, check=True)
    return Path(out.stdout.strip())


def server_program(uv: str) -> str:
    name = "tarjim-serve.exe" if sys.platform == "win32" else "tarjim-serve"
    return str(tool_bin(uv) / name)


KEEP_ENV = ("PYTHONPATH", "TARJIM_HOME", "TARJIM_SERVER", "UV_TOOL_DIR", "UV_TOOL_BIN_DIR")
CREATE_OUTSIDE_JOB = "\n".join((
    "$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly "
    "-Property @{{ShowWindow=[uint16]0}}",
    "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
    "@{{CommandLine='{line}'; CurrentDirectory='{folder}'; ProcessStartupInformation=$si}}",
    "exit $r.ReturnValue"))


def windows_line(command: list[str], log: Path) -> str:
    settings = "".join(f'set "{k}={os.environ[k]}"&& ' for k in KEEP_ENV if os.environ.get(k))
    return f'cmd /d /s /c "{settings}{subprocess.list2cmdline(command)} >> "{log}" 2>&1"'


def spawn_outside_job(command: list[str], log: Path) -> bool:
    """Let Windows' WMI service create the process, so no job object of the chat session holds
    it (uv run forbids breakaway, and closing the session would kill the child)."""
    import base64

    script = CREATE_OUTSIDE_JOB.format(line=windows_line(command, log).replace("'", "''"),
                                       folder=str(HOME).replace("'", "''"))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                               encoded], capture_output=True, timeout=60, creationflags=NO_WINDOW,
                              check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def start_detached(command: list[str], log: Path) -> None:
    """Start a program that outlives the chat session that asked for it."""
    if sys.platform == "win32" and spawn_outside_job(command, log):
        return
    with log.open("ab") as out:
        for flags in (NO_WINDOW | DETACHED | BREAKAWAY, NO_WINDOW | DETACHED):
            try:
                subprocess.Popen(command, stdout=out, stderr=out, stdin=subprocess.DEVNULL,
                                 creationflags=flags, start_new_session=sys.platform != "win32")
                return
            except PermissionError:
                continue


def main(source: str) -> int:
    uv = shutil.which("uv")
    if not uv:
        record("failed", "uv is missing: install it from https://docs.astral.sh/uv/")
        return 1
    record("installing", "downloading the engine and its models' libraries")
    with LOG.open("ab") as out:
        done = subprocess.run(install_command(uv, source), stdout=out, stderr=out,
                              creationflags=NO_WINDOW, check=False)
    if done.returncode != 0:
        record("failed", f"install failed, see {LOG}")
        return 1
    start_detached([server_program(uv)], HOME / "server.log")
    record("done", "the engine is installed and starting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
