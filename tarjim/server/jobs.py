import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from queue import Queue

MODES = ("srt", "burn")
KEEP = 50
REASONS = [("quota", ("QuotaExhausted", "quota")), ("key", ("API key missing",)),
           ("download", ("DownloadError", "download")), ("tools", ("not found; install",))]


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
    video: Path | None = None
    outputs: list[Path] = field(default_factory=list)
    created: float = field(default_factory=time.time)

    @property
    def finished(self) -> bool:
        return self.stage in ("done", "failed")

    def view(self) -> dict[str, object]:
        return {"id": self.id, "stage": self.stage, "error": self.error,
                "error_code": self.error_code, "finished": self.finished,
                "link": self.order.source.startswith(("http://", "https://")),
                "target": self.order.target, "mode": self.order.mode,
                "title": self.order.name or (self.video.stem if self.video else self.order.source),
                "outputs": [p.name for p in self.outputs], "created": self.created}


Worker = Callable[[Task], None]


class Board:
    def __init__(self, work: Worker) -> None:
        self.tasks: dict[str, Task] = {}
        self.queue: Queue[Task] = Queue()
        self.work = work
        self.lock = threading.Lock()
        threading.Thread(target=self.loop, daemon=True).start()

    def submit(self, order: Order) -> Task:
        task = Task(order)
        with self.lock:
            self.tasks[task.id] = task
            for old in sorted(self.tasks.values(), key=lambda t: t.created)[:-KEEP]:
                self.tasks.pop(old.id, None)
        self.queue.put(task)
        return task

    def retry(self, task_id: str) -> Task | None:
        old = self.get(task_id)
        return self.submit(replace(old.order)) if old and old.stage == "failed" else None

    def get(self, task_id: str) -> Task | None:
        with self.lock:
            return self.tasks.get(task_id)

    def recent(self) -> list[Task]:
        with self.lock:
            return sorted(self.tasks.values(), key=lambda t: t.created, reverse=True)

    def loop(self) -> None:
        while True:
            task = self.queue.get()
            try:
                self.work(task)
                task.stage = "done"
            except Exception as error:
                task.stage, task.error = "failed", str(error)[:300]
                task.error_code = classify(error)
