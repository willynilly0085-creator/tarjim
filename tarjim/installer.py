"""Install the tarjim engine for someone who only has the chat plugin, then start it; and replace
a running engine with a newer release.

Runs as its own hidden background process (standard library only, so a copy of this one file can
run outside the engine's own folder while that folder is replaced) and records its progress in
~/.tarjim/install.json, or ~/.tarjim/update.json for an update.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

if __package__:
    from tarjim import release_pins
else:  # the copy in ~/.tarjim, beside its own copy of release_pins
    import release_pins  # type: ignore[no-redef]

Tested, install_command = release_pins.Tested, release_pins.install_command

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
STATE = HOME / "install.json"
UPDATE_STATE = HOME / "update.json"
LOG = HOME / "install.log"
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
BREAKAWAY = 0x01000000 if sys.platform == "win32" else 0
EXIT_WAIT, STILL_ACTIVE = 90, 259


def record(state: str, detail: str = "", target: Path = STATE) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"state": state, "detail": detail, "at": time.time(),
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


def tool_bin(uv: str) -> Path:
    out = subprocess.run([uv, "tool", "dir", "--bin"], capture_output=True, text=True,
                         creationflags=NO_WINDOW, check=True)
    return Path(out.stdout.strip())


def server_program(uv: str) -> str:
    name = "tarjim-serve.exe" if sys.platform == "win32" else "tarjim-serve"
    return str(tool_bin(uv) / name)


KEEP_ENV = ("PYTHONPATH", "TARJIM_HOME", "TARJIM_SERVER", "UV_TOOL_DIR", "UV_TOOL_BIN_DIR",
            "TARJIM_RELEASES", "TARJIM_ARCHIVE")
CREATE_OUTSIDE_JOB = "\n".join((
    "$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly "
    "-Property @{{ShowWindow=[uint16]0}}",
    "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
    "@{{CommandLine='{line}'; CurrentDirectory='{folder}'; ProcessStartupInformation=$si}}",
    "exit $r.ReturnValue"))


def module_command(module: str, python: str = sys.executable) -> list[str]:
    """-P keeps the current folder off the import path: tarjim often starts in a folder it did not
    choose (the one a chat tool is open in), and a `tarjim` there must not stand in for tarjim."""
    return [python, "-P", "-m", module]


def safe_command(command: list[str]) -> list[str]:
    """Start commands saved by older versions lack -P."""
    return [command[0], "-P", *command[1:]] if command[1:2] == ["-m"] else command


def import_path() -> str:
    """PYTHONPATH without empty or relative entries, which also stand for the current folder."""
    entries = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    return os.pathsep.join(entry for entry in entries if os.path.isabs(entry))


def child_environment() -> dict[str, str]:
    env = {**os.environ, "PYTHONPATH": import_path()}
    return env if env["PYTHONPATH"] else {k: v for k, v in env.items() if k != "PYTHONPATH"}


def windows_line(command: list[str], log: Path) -> str:
    kept = {k: os.environ[k] for k in KEEP_ENV if os.environ.get(k)}
    kept["PYTHONPATH"] = import_path()  # always set: empty clears one set for the whole computer
    settings = "".join(f'set "{k}={v}"&& ' for k, v in kept.items())
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


def start_detached(command: list[str], log: Path, here: Path | None = None) -> bool:
    """Start a program that outlives the chat session; `here`: in this folder and environment."""
    if sys.platform == "win32" and not here and spawn_outside_job(command, log):
        return True
    try:
        out = log.open("ab")
    except PermissionError:  # held shut by the cmd `>>` the running engine was started with
        out = log.with_name(f"{log.stem}-restart{log.suffix}").open("ab")
    with out:
        # A console of its own that is never shown, not none at all: uv makes a virtual
        # environment's pythonw.exe a console launcher, and the Python it starts opened a
        # window when it found no console to share (Windows ignores NO_WINDOW with DETACHED).
        for flags in (NO_WINDOW | BREAKAWAY, NO_WINDOW):
            try:
                subprocess.Popen(command, stdout=out, stderr=out, stdin=subprocess.DEVNULL,
                                 cwd=here or log.parent, env=child_environment(),
                                 creationflags=flags, start_new_session=sys.platform != "win32")
                return True
            except PermissionError:
                continue
    return False


def wait_for_exit(pid: int) -> None:
    """The engine being replaced closes itself; its files cannot be replaced while it runs."""
    until = time.time() + EXIT_WAIT
    while pid and alive(pid) and time.time() < until:
        time.sleep(1)


def run_install(command: list[str]) -> int:
    with LOG.open("ab") as out:
        return subprocess.run(command, stdout=out, stderr=out, creationflags=NO_WINDOW,
                              check=False).returncode


def install(uv: str, source: str) -> int:
    """Tested versions this computer cannot meet (an older graphics card's PyTorch, say): the
    install is tried again the way it was before them."""
    pins = release_pins.tested_versions(source, HOME)
    lifted = release_pins.tested_versions(source, HOME, release_pins.OVERRIDES) if pins else None
    python = release_pins.python_for(source, HOME)
    code = run_install(install_command(uv, source, Tested(pins, lifted, python)))
    if code and pins:
        release_pins.note(HOME, "the install with tested versions failed; trying without them")
        code = run_install(install_command(uv, source, Tested(python=python)))
    return code


def main(source: str, after: int = 0, port: int = 0) -> int:
    state = UPDATE_STATE if after else STATE
    uv = shutil.which("uv")
    if not uv:
        record("failed", "uv is missing: install it from https://docs.astral.sh/uv/", state)
        return 1
    wait_for_exit(after)
    record("installing", "downloading the engine and its models' libraries", state)
    done = install(uv, source)
    start_detached([server_program(uv), *(["--port", str(port)] if port else [])],
                   HOME / "server.log")
    if done != 0:
        record("failed", f"install failed, see {LOG}", state)
        return 1
    record("done", "the engine is installed and starting", state)
    return 0


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("source", nargs="?", default=".")
    options.add_argument("--after", type=int, default=0)
    options.add_argument("--port", type=int, default=0)
    chosen = options.parse_args()
    raise SystemExit(main(chosen.source, chosen.after, chosen.port))
