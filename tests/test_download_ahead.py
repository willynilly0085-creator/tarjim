"""While a job runs, the next queued link downloads beside it (server/ahead.py)."""
import threading
from pathlib import Path
from typing import Any

import pytest

from tarjim.job import checkpoint, progress
from tarjim.server import ahead as ahead_module
from tarjim.server.ahead import Ahead
from tarjim.server.jobs import Order, Task

LINK = "https://example.com/watch?v=1"


class Jobs:
    def __init__(self, *tasks: Task) -> None:
        self.tasks = list(tasks)

    def recent(self) -> list[Task]:
        return list(self.tasks)


def board_with(running: bool) -> tuple[Jobs, Task]:
    waiting = Task(Order(LINK))
    other = Task(Order("https://example.com/watch?v=0"))
    other.stage = "translating" if running else "done"
    return Jobs(other, waiting), waiting


def ahead_over(jobs: Jobs, tmp_path: Path) -> Ahead:
    ahead = Ahead(tmp_path)
    ahead.board = jobs  # type: ignore[assignment]
    return ahead


def downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
              gate: threading.Event | None = None) -> list[str]:
    asked: list[str] = []

    def fake_download(url: str, folder: Path, _quality: str = "") -> Path:
        asked.append(url)
        progress(5, 10)
        while gate is not None and not gate.wait(0.01):
            checkpoint()
        path = folder / "clip.mp4"
        path.write_bytes(b"video")
        return path

    monkeypatch.setattr(ahead_module, "download", fake_download)
    return asked


def settle(ahead: Ahead) -> None:
    for done in list(ahead.working.values()):
        assert done.wait(5)


def test_the_next_link_downloads_while_a_job_runs(monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path: Path) -> None:
    jobs, waiting = board_with(running=True)
    asked = downloads(monkeypatch, tmp_path)
    ahead = ahead_over(jobs, tmp_path)
    ahead.consider()
    settle(ahead)
    assert asked == [LINK] and waiting.moved == (5, 10)
    assert ahead.take(waiting) == tmp_path / "clip.mp4"
    ahead.consider()
    settle(ahead)
    assert asked == [LINK]  # never downloaded twice


def test_nothing_downloads_ahead_when_no_job_runs(monkeypatch: pytest.MonkeyPatch,
                                                  tmp_path: Path) -> None:
    jobs, waiting = board_with(running=False)
    asked = downloads(monkeypatch, tmp_path)
    ahead = ahead_over(jobs, tmp_path)
    ahead.consider()
    assert asked == [] and ahead.take(waiting) is None


def test_a_paused_queued_job_gives_its_download_up(monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path: Path) -> None:
    jobs, waiting = board_with(running=True)
    gate = threading.Event()
    asked = downloads(monkeypatch, tmp_path, gate)
    ahead = ahead_over(jobs, tmp_path)
    ahead.consider()
    waiting.control = "paused"  # it must not hold the downloader the running job may need
    settle(ahead)
    assert asked == [LINK] and not (tmp_path / "clip.mp4").exists()
    waiting.control = "run"
    assert ahead.take(waiting) is None  # the job downloads it itself


def test_a_job_whose_turn_came_waits_for_its_download(monkeypatch: pytest.MonkeyPatch,
                                                      tmp_path: Path) -> None:
    jobs, waiting = board_with(running=True)
    gate = threading.Event()
    downloads(monkeypatch, tmp_path, gate)
    ahead = ahead_over(jobs, tmp_path)
    ahead.consider()
    taken: list[Any] = []
    job = threading.Thread(target=lambda: taken.append(ahead.take(waiting)))
    job.start()
    job.join(0.2)
    assert job.is_alive()  # waiting, not downloading a second time
    gate.set()
    job.join(5)
    assert taken == [tmp_path / "clip.mp4"]


def test_a_failed_download_ahead_leaves_it_to_the_job(monkeypatch: pytest.MonkeyPatch,
                                                      tmp_path: Path) -> None:
    jobs, waiting = board_with(running=True)

    def broken(_url: str, _folder: Path, _quality: str = "") -> Path:
        raise RuntimeError("HTTP Error 403")

    monkeypatch.setattr(ahead_module, "download", broken)
    ahead = ahead_over(jobs, tmp_path)
    ahead.consider()
    settle(ahead)
    assert ahead.take(waiting) is None
