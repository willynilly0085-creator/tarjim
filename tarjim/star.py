"""A quiet request for a star on GitHub, once tarjim has been of use (2026-11-22).

The engine counts the translations that finished, and after AFTER of them the add-on and the page
show a small card with three choices: star, remind me later (back after LATER), no thanks (never
again). A star is given only when the person presses the button: the engine then stars with the
person's own GitHub command (`gh`) when it is installed and signed in, and otherwise the card opens
the repository's page for the person to star there. Nothing is sent anywhere but GitHub, nothing is
tracked, and the answer is kept on this computer only (star.json beside config.json).
"""
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from tarjim import config

AFTER = 5  # translations that finished before the card is shown; the one place to change it
LATER = 14 * 24 * 3600  # "remind me later" brings the card back after this many seconds
REPO = "willynilly0085-creator/tarjim"
PAGE = f"https://github.com/{REPO}"
FILE = "star.json"
FINAL = ("never", "starred", "opened")  # answers after which the card never comes back
CHOICES = ("star", "later", "never")
WAIT = 15  # seconds a gh command may take
PLACES = ("/opt/homebrew/bin/gh", "/usr/local/bin/gh", str(Path.home() / ".local/bin/gh"))
KEEPING = threading.Lock()


def path() -> Path:
    return config.HOME / FILE


def read() -> dict[str, Any]:
    try:
        found = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"done": 0, "answer": "", "until": 0.0}
    found = found if isinstance(found, dict) else {}
    return {"done": int(found.get("done") or 0), "answer": str(found.get("answer") or ""),
            "until": float(found.get("until") or 0)}


def write(state: dict[str, Any]) -> None:
    with config.SAVING:
        config.write_json(path(), state)


def counted() -> None:
    """One more translation finished. A count that cannot be written is skipped: it never
    touches the job that finished."""
    with KEEPING:
        state = read()
        try:
            write({**state, "done": state["done"] + 1})
        except OSError:
            return


def due(state: dict[str, Any], now: float) -> bool:
    if state["answer"] in FINAL:
        return False
    if state["answer"] == "later" and now < state["until"]:
        return False
    return bool(state["done"] >= AFTER)


def view(now: float | None = None) -> dict[str, Any]:
    return {"ask": due(read(), time.time() if now is None else now), "page": PAGE}


def gh_program() -> str:
    return shutil.which("gh") or next((p for p in PLACES if Path(p).is_file()), "")


def runs(command: list[str]) -> bool:
    try:
        done = subprocess.run(command, capture_output=True, timeout=WAIT, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def star_with_gh() -> bool:
    """The person's own gh stars the repository; False when it is missing, signed out or fails."""
    gh = gh_program()
    return bool(gh) and runs([gh, "auth", "status", "--hostname", "github.com"]) and runs(
        [gh, "api", "-X", "PUT", f"/user/starred/{REPO}", "--silent"])


def answer(choice: str, now: float | None = None) -> dict[str, Any]:
    """The person's press. A star that gh could not give opens the page instead, and the card
    does not come back either way: the page was put in front of the person once."""
    if choice not in CHOICES:
        raise ValueError(choice)
    moment = time.time() if now is None else now
    kept = choice
    if choice == "star":
        kept = "starred" if star_with_gh() else "opened"
    with KEEPING:
        write({**read(), "answer": kept, "until": moment + LATER if kept == "later" else 0.0})
    return {"answer": kept, "page": PAGE}
