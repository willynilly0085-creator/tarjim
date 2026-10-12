"""Try again before giving up: a large download over a slow line drops now and then, and resumes."""
import time
from collections.abc import Callable

TRIES = 4
PAUSE = 5.0


def patiently(action: Callable[[], None], tries: int = TRIES, pause: float = PAUSE) -> None:
    for attempt in range(tries):
        try:
            return action()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(pause)
