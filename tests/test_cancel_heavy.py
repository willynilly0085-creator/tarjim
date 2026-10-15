"""A heavy model on this computer (hearing, timing, the own voice, voice separation) cannot be
stopped halfway. When a cancelled job is still inside one, the next job goes on with everything
else but loads no heavy model of its own until the old one has left, and nothing frees a model
another job is using."""
import threading
import time
from collections.abc import Callable

import pytest

from tarjim import memory
from tarjim.server.jobs import Board, Order, Task

SOON = 2.0


def until(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(0.02)
    return check()


class Models:
    """The job named "old" is halfway through a model that cannot be stopped; the others
    start, then load a model of their own."""

    def __init__(self) -> None:
        self.inside, self.leave = threading.Event(), threading.Event()
        self.steps: list[str] = []

    def __call__(self, task: Task) -> None:
        name = task.order.source
        if name == "old":
            with memory.heavy():
                self.inside.set()
                self.steps.append("old in")
                self.leave.wait(30)
                self.steps.append("old out")
            task.checkpoint()
            return
        task.stage = "hearing"
        self.steps.append(f"{name} started")
        with memory.heavy():
            self.steps.append(f"{name} in")


def test_the_next_job_waits_for_the_model_a_cancelled_job_is_still_using() -> None:
    work = Models()
    board = Board(work)
    old, new = board.submit(Order("old")), board.submit(Order("new"))
    assert work.inside.wait(5)
    board.steer(old.id, "cancel", "test")
    assert until(lambda: "new started" in work.steps, SOON)
    time.sleep(0.5)
    assert "new in" not in work.steps and old.stage == "cancelled"
    work.leave.set()
    assert until(lambda: new.stage == "done")
    assert work.steps == ["old in", "new started", "old out", "new in"]


def test_a_job_cancelled_while_waiting_for_a_model_never_loads_it() -> None:
    work = Models()
    board = Board(work)
    old, waiting = board.submit(Order("old")), board.submit(Order("waiting"))
    last = board.submit(Order("last"))
    assert work.inside.wait(5)
    board.steer(old.id, "cancel", "test")
    assert until(lambda: waiting.stage == "hearing", SOON)
    board.steer(waiting.id, "cancel", "test")
    assert until(lambda: last.stage == "hearing", SOON)
    work.leave.set()
    assert until(lambda: last.stage == "done")
    time.sleep(0.3)
    assert "waiting in" not in work.steps and work.steps[-1] == "last in"
    assert waiting.stage == "cancelled"


def test_no_model_is_freed_while_a_job_is_using_one(monkeypatch: pytest.MonkeyPatch) -> None:
    freed: list[str] = []
    monkeypatch.setattr(memory, "release_listening", lambda: freed.append("listening"))
    monkeypatch.setattr(memory, "release_local_translator", lambda: None)
    monkeypatch.setattr(memory, "empty_card", lambda: None)
    holding, done = threading.Event(), threading.Event()

    def use() -> None:
        with memory.heavy():
            holding.set()
            done.wait(5)

    threading.Thread(target=use, daemon=True).start()
    assert holding.wait(5)
    assert memory.release_models() is False and freed == []
    voice = threading.Thread(target=memory.free_for_voice, daemon=True)
    voice.start()
    time.sleep(0.3)
    assert freed == []
    done.set()
    voice.join(5)
    assert freed == ["listening"]
    assert memory.release_models() is True
