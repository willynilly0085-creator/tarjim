"""How the chat connector talks to the local tarjim server."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tarjim.config import setting

SERVER = "http://127.0.0.1:17653"
NOT_RUNNING = "tarjim is not running. Call setup_status, then start_tarjim or install_tarjim."
# How long a tool waits for tarjim's answer, by what the engine does before it answers.
SHORT = 30.0  # reads tarjim's own state
SLOW = 120.0  # asks a program or a site: sign-in state 30 s, Antigravity's models 40 s, a link 40 s
AI = 330.0  # asks an AI: a keyed engine gives up at 300 s (engines/web.py) and says why
LATE = "tarjim has not answered yet"
AGAIN = "Ask again in a minute."


def late(wait: float, then: str) -> dict[str, Any]:
    """What a tool says when tarjim is still working after `wait` seconds: a read that runs out
    of time raises a bare TimeoutError, which would leave the tool without a word (2026-11-16)."""
    return {"error": LATE, "waited_seconds": wait,
            "detail": f"tarjim is still working on this after {wait:g} seconds; nothing has "
                      f"failed yet. {then}"}


def call(path: str, body: dict[str, Any] | None = None, wait: float = SHORT,
         then: str = AGAIN) -> Any:
    request = urllib.request.Request(
        f"{setting('server') or SERVER}{path}", method="POST" if body is not None else "GET",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Tarjim-Token": setting("token"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=wait) as reply:
            return json.loads(reply.read() or b"null")
    except urllib.error.HTTPError as error:
        return {"error": error.code, "detail": error.read().decode("utf-8", "replace")[:200]}
    except (urllib.error.URLError, ConnectionError):  # also an engine restarting mid-answer
        return {"error": NOT_RUNNING}
    except TimeoutError:
        return late(wait, then)


def fetch_text(path: str, wait: float = SHORT) -> Any:
    request = urllib.request.Request(f"{setting('server') or SERVER}{path}",
                                     headers={"X-Tarjim-Token": setting("token")})
    try:
        with urllib.request.urlopen(request, timeout=wait) as reply:
            return reply.read().decode("utf-8-sig", "replace")
    except urllib.error.URLError as error:
        return {"error": str(error)}
    except TimeoutError:
        return late(wait, AGAIN)


def wait_for(job_id: str, seconds: int, tick: float = 3.0) -> Any:
    deadline = time.monotonic() + seconds
    while True:
        job = call(f"/jobs/{job_id}")
        done = not isinstance(job, dict) or job.get("finished") or "error" in job
        if done or time.monotonic() >= deadline:
            return job
        time.sleep(tick)
