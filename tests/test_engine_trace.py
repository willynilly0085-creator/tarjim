"""An engine started without a console (pythonw at sign-in) always leaves a trace in server.log:
when it started, and how it ended, even when it fails before any of its own code runs."""
import contextlib
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tarjim.server import boot

ROOT = Path(__file__).resolve().parent.parent
BROKEN = """import sys
sys.stdout = sys.stderr = None  # what pythonw gives a program
sys.modules["tarjim.server.engine"] = None  # an import that fails, as a missing library would
"""


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TARJIM_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@contextlib.contextmanager
def windowless(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No stdout or stderr, as pythonw starts a program; the log is closed afterwards."""
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", None)
        patch.setattr(sys, "stderr", None)
        boot.open_log()
        log = sys.stdout
        assert log is not None
        try:
            yield
        finally:
            log.close()


def ends(home: Path, monkeypatch: pytest.MonkeyPatch, main: Callable[[], int]) -> str:
    with windowless(monkeypatch):
        boot.run(main)
    return (home / "server.log").read_text(encoding="utf-8")


def test_a_windowless_engine_that_fails_to_import_says_so_in_its_log(tmp_path: Path) -> None:
    (tmp_path / "sitecustomize.py").write_text(BROKEN, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT)]),
           "TARJIM_HOME": str(tmp_path / "home")}
    done = subprocess.run([sys.executable, "-P", "-m", "tarjim.server"], cwd=tmp_path, env=env,
                          capture_output=True, timeout=60, stdin=subprocess.DEVNULL, check=False)
    log = (tmp_path / "home" / "server.log").read_text(encoding="utf-8")
    assert done.returncode == 1
    assert "engine: starting, process" in log and "engine: stopped by an error:" in log
    assert "ModuleNotFoundError: import of tarjim.server.engine" in log


def test_every_line_says_when(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lines = ends(home, monkeypatch, lambda: 0).splitlines()
    assert [line.split(" engine: ")[1] for line in lines][1:] == ["stopped, exit code 0"]
    assert all(line[:4].isdigit() and line[10] == " " for line in lines)


def test_an_engine_that_stops_early_on_purpose_says_so(home: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    def leaves() -> int:
        raise SystemExit(2)  # as argparse does with an unknown option

    with pytest.raises(SystemExit):
        ends(home, monkeypatch, leaves)
    assert "stopped, exit code 2" in (home / "server.log").read_text(encoding="utf-8")


def test_an_error_is_written_whole(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fails() -> int:
        raise OSError("address already in use")

    log = ends(home, monkeypatch, fails)
    assert "Traceback" in log and "OSError: address already in use" in log


def test_a_console_or_a_chosen_file_is_left_alone(home: Path) -> None:
    before = sys.stdout
    boot.open_log()
    assert sys.stdout is before and not home.exists()


def test_the_options_are_never_written(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["tarjim-serve", "--gemini-key", "AIza-secret"])
    assert "AIza-secret" not in ends(home, monkeypatch, lambda: 0)
