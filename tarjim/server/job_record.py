"""The list of recent jobs, kept on disk so it outlives a restart of the engine or of the computer.

It is written each time a job ends or leaves the list, and read when the engine starts. Only ended
jobs are kept: a job running when the computer went off does not come back half done."""
import json
import os
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tarjim.config import HOME
from tarjim.server.jobs import Board, Order, Task

JOBS = "jobs.json"
FIELDS = ("id", "error", "error_code", "failed_at", "created")
WRITING = threading.Lock()


def write_down(board: Board, folder: Path) -> None:
    rows = [{**{name: getattr(t, name) for name in FIELDS}, "stage": t.stage,
             "order": asdict(t.order), "video": str(t.video or ""),
             "outputs": [str(p) for p in t.outputs]} for t in board.recent() if t.finished]
    with WRITING:
        draft = folder / f"{JOBS}.part"
        try:
            draft.write_text(json.dumps(rows), encoding="utf-8")
            os.replace(draft, folder / JOBS)  # whole or not at all, even if the power goes
        except OSError:
            return


def task_from(row: dict[str, Any]) -> Task:
    task = Task(Order(**row["order"]), **{name: row[name] for name in FIELDS})
    task.video = Path(row["video"]) if row["video"] else None
    task.outputs = [Path(p) for p in row["outputs"]]
    task.stage = row["stage"]  # last: nothing changes a cancelled task
    return task


def restore(board: Board, folder: Path = HOME) -> None:
    try:
        rows = json.loads((folder / JOBS).read_text(encoding="utf-8"))
        tasks = [task_from(row) for row in rows]
    except (OSError, ValueError, KeyError, TypeError):
        return
    with board.lock:
        board.tasks.update((task.id, task) for task in tasks)


def keep(board: Board, folder: Path = HOME) -> None:
    """Read the list the last engine left, then write it down at every change."""
    restore(board, folder)
    board.saved = lambda: write_down(board, folder)
