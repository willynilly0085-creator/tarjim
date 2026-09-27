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


def call(path: str, body: dict[str, Any] | None = None) -> Any:
    request = urllib.request.Request(
        f"{setting('server') or SERVER}{path}", method="POST" if body is not None else "GET",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Tarjim-Token": setting("token"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return json.loads(reply.read() or b"null")
    except urllib.error.HTTPError as error:
        return {"error": error.code, "detail": error.read().decode("utf-8", "replace")[:200]}
    except urllib.error.URLError:
        return {"error": NOT_RUNNING}


def fetch_text(path: str) -> Any:
    request = urllib.request.Request(f"{setting('server') or SERVER}{path}",
                                     headers={"X-Tarjim-Token": setting("token")})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return reply.read().decode("utf-8-sig", "replace")
    except urllib.error.URLError as error:
        return {"error": str(error)}


def wait_for(job_id: str, seconds: int, tick: float = 3.0) -> Any:
    deadline = time.monotonic() + seconds
    while True:
        job = call(f"/jobs/{job_id}")
        done = not isinstance(job, dict) or job.get("finished") or "error" in job
        if done or time.monotonic() >= deadline:
            return job
        time.sleep(tick)
