import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from queue import Empty, Queue

from tarjim.children import Family, watch

DUBBING = {"dub-gemini": "gemini", "dub-clone": "clone", "dub-studio": "studio", "dub-fish": "fish",
           "dub-fishvoice": "fish:saved", "dub-eleven": "eleven", "dub-elevenclone": "eleven:clone",
           "dub-speech": "speech"}
MODES = ("srt", "burn", *DUBBING)
KEEP = 50
PAUSE_TICK = 0.5
IDLE_SECONDS = 300.0
ENDED = ("done", "failed", "cancelled")
CONTROLS = {"pause": "paused", "resume": "run", "cancel": "cancelled"}
SIGNED_OUT = ("Failed to authenticate", "OAuth session expired", "ot logged in", "run /login",
              "login required", "ign in again")
REFUSED_ACCOUNT = ("not eligible", "Eligibility check failed", "erify your account")
NOT_MEDIA = ("not a video or sound file",)
TOO_LONG = ("longer than six hours of sound",)
A_LIST = ("this link is a list of videos",)
UPDATED = ("from 'tarjim.", "named 'tarjim.")  # its code changed on disk while it ran
REASONS = [("updated", UPDATED), ("media", NOT_MEDIA), ("long", TOO_LONG), ("list", A_LIST),
           ("account", REFUSED_ACCOUNT), ("quota", ("QuotaExhausted", "quota", " 429:")),
           ("signin", SIGNED_OUT),
           ("key", ("API key missing", "API key not valid", " 401:", " 403:")),
           ("download", ("DownloadError", "download")), ("tools", ("not found; install",)),
           ("dub", ("DubUnavailable", "VoiceError"))]


class Stopped(Exception):
    pass


def classify(error: Exception) -> str:
    text = f"{type(error).__name__} {error}"
    return next((code for code, marks in REASONS if any(m in text for m in marks)), "unknown")


@dataclass
class Order:
    source: str
    target: str = "ar"
    mode: str = "burn"
    dialect: str = "saudi"
    name: str = ""


@dataclass
class Task:
    order: Order
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: str = "queued"
    error: str = ""
    error_code: str = ""
    failed_at: str = ""
    video: Path | None = None
    outputs: list[Path] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    control: str = "run"
    moved: tuple[int, int] = (0, 0)
    family: Family = field(default_factory=Family, repr=False, compare=False)
    undo: list[Callable[[], None]] = field(default_factory=list, repr=False, compare=False)

    def __setattr__(self, name: str, value: object) -> None:
        """Once the board marked a job cancelled, a thread still finishing it (a web request
        that could not be interrupted) changes nothing the person sees."""
        if getattr(self, "stage", "") != "cancelled":
            super().__setattr__(name, value)

    def take_back(self) -> None:
        """What this run made and a cancel removes: pieces, results, work."""
        for step in list(self.undo):
            try:
                step()
            except OSError:
                continue

    @property
    def finished(self) -> bool:
        return self.stage in ENDED

    def checkpoint(self) -> None:
        while self.control == "paused":
            time.sleep(PAUSE_TICK)
        if self.control == "cancelled":
            raise Stopped

    def view(self) -> dict[str, object]:
        from tarjim.server.evidence import evidence

        detail = evidence(self.error)
        return {"id": self.id, "stage": self.stage, "error": detail,
                "error_code": self.error_code, "finished": self.finished,
                "failed_at": self.failed_at, "detail": detail,
                "paused": self.control == "paused",
                "link": self.order.source.startswith(("http://", "https://")),
                "target": self.order.target, "mode": self.order.mode,
                "title": self.order.name or (self.video.stem if self.video else self.order.source),
                "outputs": [p.name for p in self.outputs], "created": self.created,
                "progress": list(self.moved),
                "files": [str(p) for p in self.outputs]}


Worker = Callable[[Task], None]


class Board:
    """One job at a time, each in a thread of its own (see carry.py), so a cancel never waits
    for the job to reach its next step."""

    def __init__(self, work: Worker, idle: Callable[[], object] | None = None,
                 idle_after: float = IDLE_SECONDS) -> None:
        self.tasks: dict[str, Task] = {}
        self.queue: Queue[Task] = Queue()
        self.work = work
        self.idle, self.idle_after, self.busy_since_idle = idle, idle_after, False
        self.lock = threading.Lock()
        watch()
        threading.Thread(target=self.loop, daemon=True).start()

    def submit(self, order: Order) -> Task:
        task = Task(order)
        with self.lock:
            twin = self.running_twin(order)
            if twin is not None:
                return twin
            self.tasks[task.id] = task
            for old in sorted(self.tasks.values(), key=lambda t: t.created)[:-KEEP]:
                self.tasks.pop(old.id, None)
        self.queue.put(task)
        return task

    def running_twin(self, order: Order) -> Task | None:
        same = (order.source, order.target, order.mode, order.dialect)
        return next((t for t in self.tasks.values() if not t.finished and same == (
            t.order.source, t.order.target, t.order.mode, t.order.dialect)), None)

    def retry(self, task_id: str) -> Task | None:
        old = self.get(task_id)
        again = old and old.stage in ("failed", "cancelled")
        return self.submit(replace(old.order)) if old and again else None

    def steer(self, task_id: str, action: str, source: str = "") -> Task | None:
        task = self.get(task_id)
        if task is None or task.finished or action not in CONTROLS:
            return None
        print(f"job {task_id}: {action} at {task.stage} from {source or 'unknown'}", flush=True)
        task.control = CONTROLS[action]
        return task

    def get(self, task_id: str) -> Task | None:
        with self.lock:
            return self.tasks.get(task_id)

    def recent(self) -> list[Task]:
        with self.lock:
            return sorted(self.tasks.values(), key=lambda t: t.created, reverse=True)

    def next_task(self) -> Task:
        while True:
            try:
                return self.queue.get(timeout=self.idle_after)
            except Empty:
                if self.idle and self.busy_since_idle:
                    self.busy_since_idle = self.idle() is False  # a model still in use

    def may_undo(self, task: Task) -> bool:
        """A job left behind takes back what it wrote late, unless the same video is being
        worked on again (a Retry), whose files would be the same."""
        same = task.order.source
        return not any(t is not task and not t.finished and t.order.source == same
                       for t in self.recent())

    def loop(self) -> None:
        from tarjim.server.carry import carry

        while True:
            task = self.next_task()
            self.busy_since_idle = True
            carry(task, self.work, self.may_undo)
