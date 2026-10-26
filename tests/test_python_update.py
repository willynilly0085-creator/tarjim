"""The Python 3.11 under tarjim's environment keeps itself current: uv names the newest patch, and
a newer one starts one rebuild through the updater, only for the uv copy and while nothing runs."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, python_update, update
from tarjim.engines import app_install

LISTING = [
    {"version": "3.11.15", "implementation": "cpython", "variant": "default"},
    {"version": "3.11.14", "implementation": "cpython", "variant": "default"},
    {"version": "3.11.99", "implementation": "pypy", "variant": "default"},
    {"version": "3.11.98", "implementation": "cpython", "variant": "debug"},
    {"version": "3.11.97rc1", "implementation": "cpython", "variant": "default"},
    {"version": "3.12.20", "implementation": "cpython", "variant": "default"},
]
REAL_BUSY = python_update.busy


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(python_update, "running", lambda: "3.11.9")
    monkeypatch.setattr(python_update, "busy", lambda: False)
    return tmp_path


class Done:
    def __init__(self, code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode, self.stdout, self.stderr = code, stdout, stderr


def uv(monkeypatch: pytest.MonkeyPatch, install_code: int = 0) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    def run(*arguments: str, seconds: int = 0) -> Done:
        calls.append(arguments)
        if arguments[:2] == ("python", "list"):
            return Done(stdout=json.dumps(LISTING))
        return Done(install_code, stderr="error: network unreachable\n")

    monkeypatch.setattr(python_update, "uv", run)
    return calls


def updater(monkeypatch: pytest.MonkeyPatch, works: bool = True) -> list[str]:
    started: list[str] = []
    monkeypatch.setattr(update, "start", lambda tag, _port: started.append(tag) or works)
    return started


@pytest.mark.parametrize(("version", "number"), [
    ("3.11.15", 15), ("3.11.0", 0), ("3.11", -1), ("3.12.1", -1), ("3.11.15rc1", -1),
    (" 3.11.9", -1), ("3.11.١٥", -1), ("3.11.1234", -1), (None, -1)])
def test_only_exactly_three_eleven_and_a_patch_is_a_version(version: Any, number: int) -> None:
    assert python_update.patch(version) == number


def test_the_newest_plain_cpython_patch_is_picked_and_compared_by_number() -> None:
    assert python_update.newest(LISTING) == "3.11.15"
    assert python_update.newest({"not": "a list"}) == "" and python_update.newest([]) == ""
    assert python_update.newer("3.11.15", "3.11.9") and not python_update.newer("3.11.9", "3.11.15")
    assert not python_update.newer("3.11.15", "3.11.15") and not python_update.newer("3.11.15", "")


def test_a_newer_patch_starts_one_rebuild_when_idle(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = uv(monkeypatch)
    started = updater(monkeypatch)
    assert python_update.refresh(idle=True, port=17653, now=1e6)
    install = [call for call in calls if call[:2] == ("python", "install")]
    assert install and install[0][2] == "3.11.15" and "--no-bin" in install[0]
    assert started == [f"v{python_update.__version__}"]
    assert python_update.view()["state"] == "rebuilding"
    assert not python_update.refresh(idle=True, port=17653, now=1e6 + 3600)
    assert not python_update.refresh(idle=True, port=17653, now=1e6 + 25 * 3600)
    assert started == [f"v{python_update.__version__}"] and len(calls) == 3  # asked, never again


def test_the_outcome_shows_in_update_once_the_engine_is_back(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uv(monkeypatch)
    updater(monkeypatch)
    monkeypatch.setattr(update, "latest", lambda: "")
    python_update.refresh(idle=True, port=17653, now=1e6)
    (home / "update.json").write_text(json.dumps({"state": "done"}), encoding="utf-8")
    state = update.view()["python"]
    assert state["state"] == "failed" and "3.11.9" in state["detail"]
    monkeypatch.setattr(python_update, "running", lambda: "3.11.15")
    state = update.view()["python"]
    assert (state["state"], state["version"], state["latest"]) == ("done", "3.11.15", "3.11.15")


def test_a_failed_python_install_starts_no_rebuild_and_is_tried_the_next_day(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = uv(monkeypatch, install_code=2)
    started = updater(monkeypatch)
    assert not python_update.refresh(idle=True, port=17653, now=1e6)
    state = python_update.view()
    assert started == [] and state["state"] == "failed" and "network" in state["detail"]
    assert not python_update.refresh(idle=True, port=17653, now=1e6 + 25 * 3600)
    assert len([call for call in calls if call[:2] == ("python", "install")]) == 2


@pytest.mark.parametrize("why", ["busy", "automatic off", "source copy", "current", "installing"])
def test_no_rebuild_when_not_allowed_or_not_needed(
        home: Path, monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    calls = uv(monkeypatch)
    started = updater(monkeypatch)
    if why == "automatic off":
        config.save("auto_update", "no")
    if why == "source copy":
        monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    if why == "current":
        monkeypatch.setattr(python_update, "running", lambda: "3.11.15")
    if why == "installing":
        monkeypatch.setattr(python_update, "busy", REAL_BUSY)
        monkeypatch.setattr(app_install, "running", {"codex": object()})
        monkeypatch.setattr(app_install, "installing", lambda _name: True)
    assert not python_update.refresh(idle=why != "busy", port=17653, now=1e6)
    assert started == [] and (calls == [] or why == "current")


class Idle:
    def recent(self) -> list[Any]:
        return []


def test_the_watch_closes_the_engine_only_for_a_rebuild_that_started(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.server import update_routes

    closed: list[bool] = []
    monkeypatch.setattr(update_routes, "close_soon", closed.append)
    for part in (update_routes.downloader, update_routes.node_update, update_routes.ffmpeg_update):
        monkeypatch.setattr(part, "refresh", lambda idle: "")
    monkeypatch.setattr(update_routes.python_update, "refresh", lambda idle, port: idle)
    update_routes.keep_current(Idle(), 17653)  # type: ignore[arg-type]
    assert closed == [True]


def test_an_engine_on_an_older_python_moves_to_the_releases_own(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A release on 3.12 installed by an older installer (which knew only 3.11) moves itself;
    a clone moves too, but takes no patch releases of the Python it is on."""
    from tarjim import pins, python_update

    monkeypatch.setattr(pins, "python", lambda: "3.12")
    assert python_update.newer("3.12.13", "3.11.15") and python_update.newer("3.12.0", "3.11.15")
    assert not python_update.newer("3.11.16", "3.11.15") and not python_update.newer("3.12.13", "")
    monkeypatch.setattr(python_update, "running", lambda: "3.11.15")
    monkeypatch.setattr(python_update, "busy", lambda: False)
    monkeypatch.setattr(python_update.update, "automatic", lambda: True)
    monkeypatch.setattr(python_update.update, "installed_by_uv", lambda: False)
    monkeypatch.setattr(python_update.update, "from_source", lambda: True)
    assert python_update.allowed(True)
    monkeypatch.setattr(pins, "python", lambda: "3.11")
    assert not python_update.allowed(True)
