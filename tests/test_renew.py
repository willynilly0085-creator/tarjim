"""An engine whose code on disk changed restarts into it by itself, only when idle, only once,
and a job that still meets the change fails with a reason the person understands."""
import json
import os
from pathlib import Path
from typing import Any

import pytest

from tarjim import same_code
from tarjim.server import engine, renew, update_routes
from tarjim.server.jobs import Board, Order, Task, classify
from tarjim.ui_languages import FOLDER, codes

ROOT = Path(__file__).resolve().parents[1] / "tarjim"


@pytest.fixture
def code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "code"
    root.mkdir()
    (root / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (root / "memory.py").write_text("def release() -> None:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(renew, "SETTLE_SECONDS", 0)
    return root


def change(root: Path) -> None:
    (root / "__init__.py").write_text('__version__ = "1.0.1"\n', encoding="utf-8")
    (root / "memory.py").write_text("def heavy() -> None:\n    pass\n", encoding="utf-8")


def test_nothing_is_due_while_the_code_on_disk_is_the_code_running(code: Path) -> None:
    assert not renew.Renewal(same_code.Snapshot(code, "code")).due()
    assert not renew.Renewal(None).due()


def test_new_code_on_disk_is_due(code: Path) -> None:
    renewal = renew.Renewal(same_code.Snapshot(code, "code"))
    change(code)
    assert renewal.due() and renew.version_on_disk(code) == "1.0.1"


def test_code_still_being_written_or_broken_waits(
        code: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    renewal = renew.Renewal(same_code.Snapshot(code, "code"))
    change(code)
    monkeypatch.setattr(renew.time, "sleep", lambda _s: (code / "new.py").write_text("x = 1"))
    assert not renewal.due()  # a pull still writing files
    monkeypatch.setattr(renew.time, "sleep", lambda _s: None)
    (code / "new.py").write_text("def half(:\n", encoding="utf-8")
    assert not renewal.due()  # a save halfway through an edit
    (code / "new.py").write_text("def whole() -> None:\n    pass\n", encoding="utf-8")
    assert renewal.due()


class Busy:
    def __init__(self, finished: bool) -> None:
        self.task = Task(Order("https://example.com/v"), stage="done" if finished else "hearing")

    def recent(self) -> list[Task]:
        return [self.task]


@pytest.fixture
def started(code: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(renew, "HOME", tmp_path)
    monkeypatch.setattr(renew, "start_detached", lambda command, _log, here: calls.append(
        command) or True)
    monkeypatch.setattr(update_routes, "close_soon", lambda started: started)
    monkeypatch.setattr(update_routes, "look", lambda *_args: None)
    return calls


def test_restarts_only_when_idle_and_only_once(code: Path, started: list[list[str]]) -> None:
    renewal = renew.Renewal(same_code.Snapshot(code, "code"))
    change(code)
    update_routes.tick(Busy(finished=False), 17701, renewal, 1)  # type: ignore[arg-type]
    assert started == []
    for count in (2, 3, 4):
        update_routes.tick(Busy(finished=True), 17701, renewal, count)  # type: ignore[arg-type]
    assert len(started) == 1


def test_the_restarted_engine_with_the_same_code_stays(
        code: Path, started: list[list[str]]) -> None:
    change(code)
    renewal = renew.Renewal(same_code.Snapshot(code, "code"))  # the new engine's own snapshot
    update_routes.tick(Busy(finished=True), 17701, renewal, 1)  # type: ignore[arg-type]
    assert started == []


def test_the_new_engine_is_started_the_same_way_and_waits_for_this_one() -> None:
    command = renew.command(["--port", "17701", "--after", "42"])
    assert command[1:4] == ["-P", "-m", "tarjim.server"]
    assert command[4:] == ["--port", "17701", "--after", str(os.getpid())]


def test_the_engine_waits_for_the_one_it_replaces(monkeypatch: pytest.MonkeyPatch) -> None:
    waited: list[int] = []
    monkeypatch.setattr(engine, "start_up", lambda: None)
    monkeypatch.setattr(engine.same_code, "hold", lambda: None)
    monkeypatch.setattr(engine, "wait_for_exit", waited.append)
    monkeypatch.setattr(engine, "run_alongside", waited.append)
    monkeypatch.setattr(engine, "serve", lambda *_args: None)
    engine.main(["--port", "17701", "--after", "4242"])
    assert waited == [4242, 17701]


def test_the_jobs_list_survives_the_restart(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    old = Board(lambda task: None)
    failed = Task(Order("https://example.com/v", target="fr", mode="srt"))
    failed.error, failed.error_code, failed.failed_at = "cannot import", "updated", "hearing"
    failed.outputs, failed.stage = [tmp_path / "v.srt"], "failed"
    old.tasks[failed.id] = failed
    renew.write_down(old, tmp_path)
    new = Board(lambda task: None)
    renew.restore(new, tmp_path)
    assert new.get(failed.id).view() == failed.view()  # type: ignore[union-attr]
    assert new.retry(failed.id) is not None and not (tmp_path / renew.JOBS).exists()


@pytest.mark.parametrize("error", [
    ImportError("cannot import name 'heavy' from 'tarjim.memory' (C:\\t\\tarjim\\memory.py)"),
    ImportError("cannot import name 'fetch' from 'tarjim.downloader' (C:\\t\\downloader.py)"),
    ModuleNotFoundError("No module named 'tarjim.listen.vote'")])
def test_a_job_that_meets_new_code_says_so(error: Exception) -> None:
    assert classify(error) == "updated"


def test_a_missing_library_is_not_mistaken_for_an_update() -> None:
    assert classify(ImportError("cannot import name 'x' from 'transformers'")) != "updated"
    assert classify(ModuleNotFoundError("No module named 'torchaudio'")) != "updated"


def test_the_reason_is_shown_in_every_language() -> None:
    for code in codes():
        page: dict[str, Any] = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        extension = json.loads((ROOT / "extension" / "_locales" / code / "messages.json")
                               .read_text(encoding="utf-8"))
        assert page.get("err_updated") and page["retry"] in page["err_updated"], code
        assert extension["errUpdated"]["message"] == page["err_updated"], code
    assert '"updated"' in (ROOT / "web" / "jobs.js").read_text(encoding="utf-8")
    assert 'updated: "errUpdated"' in (ROOT / "extension" / "shared.js").read_text(
        encoding="utf-8")


def test_the_restart_starts_a_windowless_python(monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import autostart

    monkeypatch.setattr(autostart, "quiet_python", lambda: "C:/env/Scripts/pythonw.exe")
    command = renew.command(["--port", "17701"])
    assert command[:4] == ["C:/env/Scripts/pythonw.exe", "-P", "-m", "tarjim.server"]
