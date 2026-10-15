"""A cancel stops a job's work at once, whatever the job is doing, and the next job starts: every
program the job started is stopped with everything it started in turn, and a job stuck where
nothing can stop it (a web request in flight) is left behind to end by itself."""
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import psutil
import pytest

from tarjim.server.jobs import Board, Order, Task

SOON = 2.0
FFMPEG = shutil.which("ffmpeg")
TREE = ("import subprocess, sys, time\n"
        "kid = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "print(kid.pid, flush=True)\n"
        "time.sleep(60)\n")


def until(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return check()


def gone(pid: int) -> bool:
    try:
        return bool(psutil.Process(pid).status() == psutil.STATUS_ZOMBIE)
    except psutil.NoSuchProcess:
        return True


def held(pid: int) -> bool:
    try:
        return bool(psutil.Process(pid).status() == psutil.STATUS_STOPPED)
    except psutil.NoSuchProcess:
        return False


@pytest.fixture
def pids() -> Iterator[list[int]]:
    started: list[int] = []
    yield started
    for pid in started:  # whatever a failing test left running
        try:
            psutil.Process(pid).kill()
        except psutil.Error:
            continue


def test_a_cancel_stops_the_programs_of_a_job_and_the_next_job_starts(pids: list[int]) -> None:
    began = threading.Event()

    def work(task: Task) -> None:
        if task.order.source == "next":
            began.set()
            return
        task.stage = "downloading"
        child = subprocess.Popen([sys.executable, "-c", TREE], stdout=subprocess.PIPE, text=True)
        pids.extend([child.pid, int(child.stdout.readline())])  # type: ignore[union-attr]
        child.wait()

    board = Board(work)
    doomed, after = board.submit(Order("first")), board.submit(Order("next"))
    assert until(lambda: len(pids) == 2)
    board.steer(doomed.id, "cancel", "test")
    assert began.wait(SOON)
    assert until(lambda: all(gone(pid) for pid in pids), SOON)
    assert doomed.stage == "cancelled" and until(lambda: after.stage == "done")


class Stuck:
    """A job waiting on a web request nothing can interrupt, which then tries to report."""

    def __init__(self) -> None:
        self.gate, self.began, self.ended = threading.Event(), threading.Event(), threading.Event()

    def __call__(self, task: Task) -> None:
        if task.order.source == "next":
            self.began.set()
            return
        try:
            task.stage = "translating"
            self.gate.wait(30)
            task.stage, task.outputs = "writing", [Path("late.srt")]
            task.checkpoint()
        finally:
            self.ended.set()


def test_a_job_stuck_where_nothing_can_stop_it_is_left_behind() -> None:
    work = Stuck()
    board = Board(work)
    stuck, after = board.submit(Order("first")), board.submit(Order("next"))
    assert until(lambda: stuck.stage == "translating")
    board.steer(stuck.id, "cancel", "test")
    assert work.began.wait(SOON) and stuck.stage == "cancelled"
    work.gate.set()
    assert work.ended.wait(5)
    time.sleep(0.1)
    assert stuck.stage == "cancelled" and stuck.outputs == [] and stuck.view()["finished"]
    assert until(lambda: after.stage == "done")


def test_a_job_that_fails_for_another_reason_fails_as_before() -> None:
    def work(task: Task) -> None:
        task.stage = "translating"
        raise RuntimeError("API key not valid. Please pass a valid API key.")

    board = Board(work)
    task = board.submit(Order("x"))
    assert until(lambda: task.finished)
    assert (task.stage, task.failed_at, task.error_code) == ("failed", "translating", "key")
    assert "API key not valid" in task.error


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")
def test_a_pause_holds_ffmpeg_and_a_resume_lets_it_go_on(pids: list[int]) -> None:
    def work(task: Task) -> None:
        task.stage = "burning"
        ffmpeg = subprocess.Popen([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-re",
                                   "-f", "lavfi", "-i", "sine=d=60", "-f", "null", "-"])
        waiting = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        pids.extend([ffmpeg.pid, waiting.pid])
        ffmpeg.wait()

    board = Board(work)
    task = board.submit(Order("x"))
    assert until(lambda: len(pids) == 2)
    board.steer(task.id, "pause", "test")
    assert until(lambda: held(pids[0]), SOON) and task.view()["paused"]
    assert not held(pids[1])  # a program that may be waiting on the network is left running
    board.steer(task.id, "resume", "test")
    assert until(lambda: not held(pids[0]), SOON)
    board.steer(task.id, "pause", "test")
    assert until(lambda: held(pids[0]), SOON)
    board.steer(task.id, "cancel", "test")
    assert until(lambda: all(gone(pid) for pid in pids), SOON)
    assert until(lambda: task.stage == "cancelled", SOON)
