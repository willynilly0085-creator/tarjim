"""What the tarjim shortcut runs: start the engine when it is not running, then open its page.

The engine starts with the computer, but when it has stopped (it failed at sign-in, or someone
closed it) the person needs a way back that is not a terminal. Double-clicking the shortcut
starts it without a window, waits until it answers and opens the page; when it is already
running, the page opens at once. A second double-click while it is starting does not start a
second engine.
"""
import argparse
import json
import time
import urllib.request
import webbrowser

from tarjim.assistant_http import SERVER
from tarjim.autostart import quiet_python
from tarjim.config import setting
from tarjim.installer import HOME, module_command, start_detached

WAIT = 90.0
STARTING = HOME / "waking"


def answers(page: str) -> bool:
    try:
        with urllib.request.urlopen(f"{page}/ping", timeout=2) as reply:
            return bool(json.loads(reply.read()).get("app") == "tarjim")
    except (OSError, ValueError, AttributeError):
        return False


def start(port: int = 0) -> bool:
    """False when another double-click started it moments ago."""
    try:
        if time.time() - STARTING.stat().st_mtime < WAIT:
            return False
    except OSError:
        pass
    HOME.mkdir(parents=True, exist_ok=True)
    STARTING.touch()
    extra = ["--port", str(port)] if port else []
    return start_detached([*module_command("tarjim.server", quiet_python()), *extra],
                          HOME / "server.log")


def wait(page: str, seconds: float = WAIT, tick: float = 1.0) -> bool:
    deadline = time.monotonic() + seconds
    while not answers(page):
        if time.monotonic() > deadline:
            return False
        time.sleep(tick)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tarjim-wake", description=__doc__)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)  # tests
    args = parser.parse_args(argv)
    page = f"http://127.0.0.1:{args.port}" if args.port else (setting("server") or SERVER)
    up = answers(page)
    if not up:
        start(args.port)
        up = wait(page)
    webbrowser.open(f"{page}/")  # also when it did not start: the browser says so
    return 0 if up else 1


if __name__ == "__main__":
    raise SystemExit(main())
