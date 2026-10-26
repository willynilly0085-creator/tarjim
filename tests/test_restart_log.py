"""An engine restarts onto new code even while another program holds server.log shut.

On 2026-10-27 the owner's engine had been started behind cmd's `>>`, which keeps the log closed to
every other writer. The engine saw the update ("code changed on disk: restarting"), could not open
the log for the new engine, and kept running the old code; the browser extension stayed old too.
"""
from pathlib import Path
from typing import Any

import pytest

from tarjim import installer


class HeldShut(type(Path())):  # type: ignore[misc]
    """server.log is held shut by the running engine's cmd; any other file opens as usual."""

    def open(self, *args: Any, **kwargs: Any) -> Any:
        if self.name == "server.log":
            raise PermissionError(13, "Permission denied", str(self))
        return super().open(*args, **kwargs)


def test_a_log_held_shut_does_not_stop_the_new_engine(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[dict[str, Any]] = []
    monkeypatch.setattr(installer.subprocess, "Popen", lambda *_a, **kw: started.append(kw))
    assert installer.start_detached(["pythonw.exe", "-m", "tarjim.server"],
                                    HeldShut(tmp_path / "server.log"), here=tmp_path)
    assert Path(started[0]["stdout"].name).name == "server-restart.log"


def test_a_free_log_still_receives_the_output(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[dict[str, Any]] = []
    monkeypatch.setattr(installer.subprocess, "Popen", lambda *_a, **kw: started.append(kw))
    assert installer.start_detached(["program"], tmp_path / "server.log", here=tmp_path)
    assert Path(started[0]["stdout"].name).name == "server.log"
