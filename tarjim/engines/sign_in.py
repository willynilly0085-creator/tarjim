"""Sign in to a subscription through the browser, with no terminal window.

Claude Code and Codex open the browser themselves and finish on their own; when the sign-in page
shows a code instead, the page hands it to the waiting program. Programs without a browser sign-in
still open in a console.
"""
import json
import re
import subprocess
import sys

from tarjim.engines.catalog import BY_ID, SUBSCRIPTION
from tarjim.engines.subscription import HIDDEN, launcher

BROWSER = {"claude": (("auth", "login", "--claudeai"), ("auth", "status")),
           "codex": (("login",), ("login", "status")),
           "grok": (("login", "--oauth"), ("models",))}
CODE = re.compile(r"^[\w#.~-]{6,512}$")
STATUS_SECONDS = 30
waiting: dict[str, subprocess.Popen[str]] = {}


def open_console(command: list[str]) -> bool:
    if sys.platform != "win32" or not command:
        return False
    subprocess.Popen(["cmd", "/k", *command], creationflags=subprocess.CREATE_NEW_CONSOLE)
    return True


def start(provider: str) -> str:
    found = BY_ID.get(provider)
    program = launcher(found.program) if found and found.method == SUBSCRIPTION else []
    if not found or not program:
        return ""
    if provider not in BROWSER:
        return "console" if open_console([*program, *found.login[1:]]) else ""
    stop(provider)
    waiting[provider] = subprocess.Popen(
        [*program, *BROWSER[provider][0]], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, text=True, creationflags=HIDDEN)
    return "browser"


def stop(provider: str) -> None:
    process = waiting.pop(provider, None)
    if process is not None and process.poll() is None:
        process.kill()


def send_code(provider: str, code: str) -> bool:
    process = waiting.get(provider)
    if process is None or process.poll() is not None or not CODE.match(code) or not process.stdin:
        return False
    process.stdin.write(code + "\n")
    process.stdin.flush()
    return True


def signed_in(provider: str) -> bool:
    program = launcher(BY_ID[provider].program) if provider in BROWSER else []
    if not program:
        return False
    try:
        done = subprocess.run([*program, *BROWSER[provider][1]], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=STATUS_SECONDS,
                              creationflags=HIDDEN, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if provider == "claude":
        try:
            return bool(json.loads(done.stdout).get("loggedIn"))
        except ValueError:
            return False
    if provider == "grok":
        from tarjim.engines.grok import signed_in as grok_signed_in

        return done.returncode == 0 and grok_signed_in(done.stdout)
    return done.returncode == 0 and "not logged in" not in done.stdout.lower()
