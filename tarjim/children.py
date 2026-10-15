"""Every program a job starts belongs to that job. A cancel stops all of them at once, with
everything they started in turn (a downloader's ffmpeg, a subscription app's own helpers),
instead of waiting for the job's next step. A pause holds the ones that work only on files on
this computer (ffmpeg extracting, burning, mixing); a program reading from the web is left
running, because holding it for minutes would drop its connection and fail the job."""
import subprocess
import threading
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import psutil

FAMILY: ContextVar["Family | None"] = ContextVar("family", default=None)
LOCAL = ("ffmpeg", "ffprobe")
GONE_SECONDS = 1.0
Child = subprocess.Popen[Any]


def act(step: Any) -> bool:
    try:
        step()
    except psutil.Error:
        return False
    return True


def tree(child: Child) -> list[Any]:
    """The program and everything it started. Its returncode is set only once it was waited
    for, so until then its number cannot have been given to another program."""
    if child.returncode is not None:
        return []
    try:
        root = psutil.Process(child.pid)
        return [root, *root.children(recursive=True)]
    except psutil.Error:
        return []


def alive(process: Any) -> bool:
    try:
        return bool(process.is_running() and process.status() != psutil.STATUS_ZOMBIE)
    except psutil.Error:
        return False


def end(processes: list[Any]) -> None:
    """Kill, then wait until they are gone (files they held can then be removed). Not waited
    for with psutil, which would reap a direct child and hide its exit code from its caller."""
    for process in processes:
        act(process.kill)
    deadline = time.monotonic() + GONE_SECONDS
    while any(alive(p) for p in processes) and time.monotonic() < deadline:
        time.sleep(0.02)


def local(child: Child) -> bool:
    command = [str(a) for a in child.args] if isinstance(child.args, list) else [str(child.args)]
    reads_web = any("://" in part for part in command)
    return Path(command[0]).stem.lower() in LOCAL and not reads_web


class Family:
    """The programs one job started."""

    def __init__(self) -> None:
        self.members: list[Child] = []
        self.held: dict[int, Any] = {}
        self.stopped = False
        self.lock = threading.Lock()

    def add(self, child: Child) -> None:
        with self.lock:
            self.members.append(child)
            late = self.stopped
        if late:  # started by a cancelled job that had not reached its next step yet
            end(tree(child))

    def everyone(self, only_local: bool = False) -> list[Any]:
        with self.lock:
            members = [c for c in self.members if not only_local or local(c)]
        return [process for child in members for process in tree(child)]

    def stop(self) -> None:
        """Held first, so none can start another program while the rest are being stopped."""
        with self.lock:
            self.stopped = True
        first = self.everyone()
        for process in first:
            act(process.suspend)
        found = {p.pid: p for p in [*first, *self.everyone()]}
        end(list(found.values()))

    def hold(self) -> None:
        for process in self.everyone(only_local=True):
            if process.pid not in self.held and act(process.suspend):
                self.held[process.pid] = process

    def release(self) -> None:
        for process in self.held.values():
            act(process.resume)
        self.held.clear()


def watch() -> None:
    """Remember each program with the job whose thread started it."""
    if getattr(subprocess.Popen, "_tarjim_family", False):
        return
    original = subprocess.Popen.__init__

    def start(self: Child, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        family = FAMILY.get()
        if family is not None:
            family.add(self)

    setattr(subprocess.Popen, "__init__", start)  # noqa: B010
    setattr(subprocess.Popen, "_tarjim_family", True)  # noqa: B010
