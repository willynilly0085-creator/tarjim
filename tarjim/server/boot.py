"""The first thing an engine does: make sure it leaves a trace.

The sign-in launch starts the engine with pythonw, which gives it no stdout or stderr, so an error
before the engine attached its log vanished: on 2026-10-24 an engine started at sign-in was gone a
minute later with no line in server.log. This module needs only the standard library and runs
before any other tarjim code, so even an import that fails is written down, with the time.
"""
import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

OWNER_DIR = 0o700


def log_path() -> Path:
    """config.HOME's server.log, without importing config."""
    return Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim")) / "server.log"


def open_log() -> None:
    """Under pythonw both outputs go to the log; a console or a file the starter chose stays.
    The sign-in script asks for the log by name: the pythonw.exe uv writes into a virtual
    environment is a console launcher, so the engine got a hidden console that swallowed it all."""
    if sys.stdout is not None and not os.environ.get("TARJIM_LOG_TO_FILE"):
        return
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=OWNER_DIR)
        sys.stdout = sys.stderr = path.open("a", encoding="utf-8", buffering=1)
    except OSError:
        return


def note(line: str) -> None:
    stamp = datetime.now().astimezone().isoformat(sep=" ", timespec="seconds")
    print(f"{stamp} engine: {line}", file=sys.stderr, flush=True)


def run(main: Callable[[], int]) -> int:
    """Runs the engine and writes how it ended. The options are not written: one may be a key."""
    note(f"starting, process {os.getpid()}, {sys.executable}")
    try:
        code = main()
    except SystemExit as stop:
        note(f"stopped, exit code {stop.code}")
        raise
    except Exception:
        note("stopped by an error:")
        traceback.print_exc()
        return 1
    note(f"stopped, exit code {code}")
    return code
