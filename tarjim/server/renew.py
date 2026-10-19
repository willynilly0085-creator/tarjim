"""An engine whose code on disk changed restarts into it by itself, when nothing is running.

People who run tarjim from a clone update it with `git pull` while the engine runs. The engine
keeps running the code it started with (same_code.py) and, once a minute in the update watch,
compares its files' sizes and times with those it read at start. New code that has stopped
changing for a few seconds and compiles is taken up the way an update is: the engine starts a copy
of itself with the same command line, which waits for this one to close before taking the port,
then closes. The list of jobs goes along, so a failed job keeps its Try again. The new engine reads
the new code at its own start, so it sees nothing to restart for: no loop.
"""
import json
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tarjim import same_code
from tarjim.config import HOME
from tarjim.installer import module_command, start_detached
from tarjim.server.jobs import Board, Order, Task

SETTLE_SECONDS = 5.0
JOBS = "jobs.json"
FIELDS = ("id", "error", "error_code", "failed_at", "created")


def own_arguments(argv: list[str]) -> list[str]:
    """The engine's own options, without the --after of the restart that started it."""
    return [arg for arg, before in zip(argv, ["", *argv], strict=False)
            if "--after" not in (arg, before) and not arg.startswith("--after=")]


def command(argv: list[str] | None = None) -> list[str]:
    """pythonw on Windows: a virtual environment's python.exe is a launcher whose real Python opens
    a console window of its own, even when the launcher was started without one."""
    from tarjim.autostart import quiet_python

    own = own_arguments(sys.argv[1:] if argv is None else argv)
    return [*module_command("tarjim.server", quiet_python()), *own, "--after", str(os.getpid())]


def compiles(root: Path) -> bool:
    try:
        for path in same_code.files(root):
            compile(path.read_bytes(), str(path), "exec")
    except (OSError, SyntaxError, ValueError):
        return False
    return True


def version_on_disk(root: Path) -> str:
    try:
        found = re.search(r'__version__ = "([^"]+)"', (root / "__init__.py").read_text("utf-8"))
    except OSError:
        return "?"
    return found.group(1) if found else "?"


def write_down(board: Board, folder: Path) -> None:
    rows = [{**{name: getattr(t, name) for name in FIELDS}, "stage": t.stage,
             "order": asdict(t.order), "video": str(t.video or ""),
             "outputs": [str(p) for p in t.outputs]} for t in board.recent() if t.finished]
    (folder / JOBS).write_text(json.dumps(rows), encoding="utf-8")


def task_from(row: dict[str, Any]) -> Task:
    task = Task(Order(**row["order"]), **{name: row[name] for name in FIELDS})
    task.video = Path(row["video"]) if row["video"] else None
    task.outputs = [Path(p) for p in row["outputs"]]
    task.stage = row["stage"]  # last: nothing changes a cancelled task
    return task


def restore(board: Board, folder: Path = HOME) -> None:
    path = folder / JOBS
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        path.unlink()
        tasks = [task_from(row) for row in rows]
    except (OSError, ValueError, KeyError, TypeError):
        return
    with board.lock:
        board.tasks.update((task.id, task) for task in tasks)


class Renewal:
    def __init__(self, snapshot: same_code.Snapshot | None) -> None:
        self.snapshot, self.started = snapshot, False

    def due(self) -> bool:
        """New code on disk, no longer being written (a pull, an edit) and whole enough to run."""
        if self.snapshot is None or self.started or not self.snapshot.changed():
            return False
        before = same_code.fingerprint(self.snapshot.root)
        time.sleep(SETTLE_SECONDS)
        return same_code.fingerprint(self.snapshot.root) == before and compiles(
            self.snapshot.root)

    def restart(self, board: Board) -> bool:
        """At most once: a copy that fails to start leaves this engine running as it was."""
        self.started = True
        root = self.snapshot.root if self.snapshot else same_code.ROOT
        print(f"tarjim's code changed on disk ({version_on_disk(root)}): restarting to use it",
              flush=True)
        write_down(board, HOME)
        return start_detached(command(), HOME / "server.log", here=Path.cwd())
