"""A job asked for while the engine closes, or waiting when the computer went off, is not lost."""
import threading
from pathlib import Path

from tarjim.server.job_record import keep, write_down
from tarjim.server.jobs import Board, Order, Task


def test_a_job_asked_for_while_closing_waits_for_the_next_engine(tmp_path: Path) -> None:
    ran: list[str] = []
    closing = Board(lambda task: ran.append(task.order.source))
    keep(closing, tmp_path)
    closing.closing = True
    asked = closing.submit(Order("https://x.com/v/1"))
    assert asked.stage == "queued" and not ran

    started = threading.Event()
    next_engine = Board(lambda task: started.set())
    keep(next_engine, tmp_path)
    assert started.wait(5)
    assert next_engine.get(asked.id) is not None


def test_a_running_job_is_not_brought_back_half_done(tmp_path: Path) -> None:
    board = Board(lambda task: None)
    running = Task(Order("a"))
    running.stage = "translating"
    board.tasks[running.id] = running
    write_down(board, tmp_path)
    assert running.id not in (tmp_path / "jobs.json").read_text(encoding="utf-8")


def test_an_error_in_one_job_does_not_stop_the_queue() -> None:
    done = threading.Event()

    def work(task: Task) -> None:
        if task.order.source == "second":
            done.set()

    board = Board(work)
    board.saved = lambda: (_ for _ in ()).throw(OSError("disk full"))
    board.submit(Order("first"))
    board.submit(Order("second"))
    assert done.wait(5)


def test_no_restart_while_a_tool_downloads(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from tarjim.server import update_routes
    from tarjim.tools import Progress, shelf

    board = Board(lambda task: None)
    assert update_routes.idle(board)
    tool = next(iter(shelf().progress))
    monkeypatch.setitem(shelf().progress, tool, Progress("downloading"))
    assert not update_routes.idle(board)
