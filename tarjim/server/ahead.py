"""The next link downloads while the job before it is still working.

A job spends most of its time hearing, timing, translating and burning, and the link queued
after it used to wait for all of that before its download even began. Now, while a job runs,
the earliest queued link downloads beside it into the same folder. It is still one download at
a time (fetch.IN_USE): this only lets a download overlap the work of the job before.

A queued job that is paused or cancelled gives its download up at once, so it never holds the
downloader that the running job may need. Once its own turn has come, the job waits for the
download already under way (and its pause and cancel act on it as on its own); anything that
went wrong ahead is not told: the job downloads the link itself and says the real reason.
"""
import contextlib
import threading
import time
from contextvars import copy_context
from pathlib import Path

from tarjim.fetch import download, is_url
from tarjim.job import CHECKPOINT, PROGRESS
from tarjim.server.jobs import ENDED, Board, Stopped, Task

LOOK_EVERY = 2.0
WAIT_TICK = 0.5


class Ahead:
    board: Board | None

    def __init__(self, folder: Path) -> None:
        self.folder, self.board = folder, None
        self.lock = threading.Lock()
        self.claimed: set[str] = set()  # jobs whose turn came: their download is theirs now
        self.tried: set[str] = set()  # downloaded ahead, or given up: never tried twice
        self.made: dict[str, Path] = {}
        self.working: dict[str, threading.Event] = {}

    def watch(self, board: Board) -> None:
        self.board = board
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self) -> None:
        while True:  # an error in one look never stops the next
            time.sleep(LOOK_EVERY)
            with contextlib.suppress(Exception):
                self.consider()

    def consider(self) -> None:
        with self.lock:
            task = None if self.working else self.next_link()
            if task is None:
                return
            done = self.working[task.id] = threading.Event()
        threading.Thread(target=copy_context().run, args=(self.fetch, task, done),
                         daemon=True).start()

    def next_link(self) -> Task | None:
        """The earliest queued link not tried yet, while another job is running."""
        jobs = self.board.recent() if self.board else []
        if not any(t.stage not in ("queued", *ENDED) for t in jobs):
            return None  # nothing runs: the queued job starts now and downloads it itself
        skip = self.tried | self.claimed
        waiting = [t for t in jobs if t.stage == "queued" and t.control == "run"
                   and is_url(t.order.source) and t.id not in skip]
        return min(waiting, key=lambda t: t.created, default=None)

    def fetch(self, task: Task, done: threading.Event) -> None:
        CHECKPOINT.set(lambda: self.still_wanted(task))
        PROGRESS.set(lambda got, total: setattr(task, "moved", (got, total)))
        try:
            path = download(task.order.source, self.folder, task.order.quality)
            with self.lock:
                self.made[task.id] = path
            print(f"job {task.id}: downloaded while the job before it ran", flush=True)
        except Exception as error:  # the job downloads it itself and tells the real reason
            print(f"job {task.id}: the download ahead stopped ({type(error).__name__}); "
                  "the job downloads it itself", flush=True)
        finally:
            with self.lock:
                self.working.pop(task.id, None)
                self.tried.add(task.id)
            done.set()

    def still_wanted(self, task: Task) -> None:
        if task.id in self.claimed:
            task.checkpoint()  # its turn came: a pause holds it, as the job's own would
        elif task.control != "run":
            raise Stopped

    def take(self, task: Task) -> Path | None:
        """The file downloaded ahead for this job, waiting for one under way; or nothing."""
        with self.lock:
            self.claimed.add(task.id)
            done = self.working.get(task.id)
        while done is not None and not done.wait(WAIT_TICK):
            task.checkpoint()
        with self.lock:
            path = self.made.pop(task.id, None)
        return path if path is not None and path.is_file() else None
