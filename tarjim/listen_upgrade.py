"""Local listening moves onto the Transformers-native Qwen3-ASR pair by itself, never leaving the
person without it.

A computer that listened with the earlier pair (the qwen-asr package's format) keeps listening
with it, through the same classes (tarjim/asr/qwen_load.py). While tarjim is idle, the update
watch starts the native pair's download in the background, the way Settings would (the
listening tool shows it, and so do list_tools and setup_status in chat); its large files continue
where they stopped (tarjim/hub_fetch.py) and count only when their SHA-256 matches. A failed
download keeps the earlier pair and is tried again an hour later; one that would leave less than
2 GB free waits for room. With automatic updates off nothing starts by itself: Settings offers
the download instead. Once the native pair is fully here, the next job uses it, and the
earlier pair's folders are removed as soon as no job holds a model. A new install never sees the
earlier pair: Settings and the setup download only the native one.
"""
import threading
import time
from typing import Any

from tarjim.asr.qwen_load import ALIGNER_MODEL, ASR_MODEL, EARLIER_ALIGNER, EARLIER_ASR

NATIVE = (ASR_MODEL, ALIGNER_MODEL)
EARLIER = (EARLIER_ASR, EARLIER_ALIGNER)
TOOL = "accuracy"
AGAIN_SECONDS = 3600.0
SPARE_GB = 2.0
TRIED: list[float] = []
LOCK = threading.Lock()


def here(repos: tuple[str, ...]) -> bool:
    from tarjim.model_pins import ready

    return all(ready(repo) for repo in repos)


def state() -> str:
    """native: the new pair is here; earlier: only the earlier pair; none: no local listening."""
    if here(NATIVE):
        return "native"
    return "earlier" if here(EARLIER) else "none"


def listening_ready() -> bool:
    return state() != "none"


def earlier_left() -> bool:
    from tarjim.model_pins import snapshot

    return any(snapshot(repo).exists() for repo in EARLIER)


def remove_earlier() -> bool:
    """Only while no job holds a model: the engine on the earlier pair is let go first."""
    from tarjim import model_pins
    from tarjim.memory import HEAVY, empty_card, release_listening

    if not HEAVY.acquire(blocking=False):
        return False
    try:
        release_listening()
        empty_card()
        removed = [model_pins.remove(repo) for repo in EARLIER]
    except OSError as error:
        print(f"listening: the earlier models stay for now ({type(error).__name__})", flush=True)
        return False
    finally:
        HEAVY.release()
    return any(removed)


def room_for_download() -> bool:
    from tarjim.system import free_disk_gb
    from tarjim.tools import BY_ID

    return free_disk_gb() >= BY_ID[TOOL].size_gb + SPARE_GB


def due(now: float) -> bool:
    with LOCK:
        if TRIED and now - TRIED[-1] < AGAIN_SECONDS:
            return False
        TRIED.append(now)
        return True


def start_download(shelf: Any, now: float) -> str:
    if shelf.progress[TOOL].state == "downloading":
        return "downloading"
    if not room_for_download():
        return "waiting for disk space"
    if not due(now):
        return "waiting"
    return "started" if shelf.start(TOOL) == "started" else "waiting"


def step(shelf: Any, idle: bool, now: float | None = None) -> str:
    """Once a minute from the update watch; what it did, for the log and the tests."""
    from tarjim.update import automatic

    current = state()
    if current == "native":
        return "removed earlier" if earlier_left() and idle and remove_earlier() else "native"
    if current == "none" or not idle or not automatic():
        return current
    return start_download(shelf, time.time() if now is None else now)


def upgrade_view(shelf: Any) -> dict[str, Any]:
    """For the listening tool's row: the native pair's download while the earlier one listens."""
    from tarjim.update import automatic

    if state() != "earlier":
        return {}
    progress = shelf.progress[TOOL].state
    if progress in ("downloading", "failed"):
        return {"upgrade": progress}
    return {"upgrade": "waiting" if automatic() else "manual"}
