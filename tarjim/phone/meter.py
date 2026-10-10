"""How far a download or an upload is, said the same way wherever the bot moves a file: a bar of
ten cells and the megabytes so far. Telegram has no progress bar for a bot's message, so the
message draws its own."""
import time
from collections.abc import Callable

Tell = Callable[[int, int], None]
EVERY = 4.0
MB = 1024 * 1024
CELLS = 10


def bar(done: int, total: int) -> str:
    filled = min(CELLS, round(CELLS * done / max(total, 1)))
    return "▰" * filled + "▱" * (CELLS - filled)


def amount(done: int, total: int) -> str:
    """The bar with the megabytes so far; both numbers are megabytes."""
    from tarjim.phone.words import say

    return f"{bar(done, total)} " + say("phone_progress", done=done, total=total)


def shown(step: str, done: int, total: int) -> str:
    return "\n".join((step, amount(done, total)))


class Meter:
    """Tell how far a transfer is, in megabytes, at most once every few seconds. A message that
    cannot be shown never stops the transfer."""

    def __init__(self, tell: Tell) -> None:
        self.tell, self.last = tell, 0.0

    def __call__(self, done: int, total: int) -> None:
        if not total or time.monotonic() - self.last < EVERY:
            return
        self.last = time.monotonic()
        try:
            self.tell(round(done / MB), max(1, round(total / MB)))
        except Exception:
            return
