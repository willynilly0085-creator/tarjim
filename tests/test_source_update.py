"""A copy run from source updates by itself: the clone moves to the release's tag only as a
fast-forward, its libraries move to the tested versions, and a failure puts the code back.
Real git on repositories made here; uv is replaced where it would install."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim import config, installer, source_updater, update

pytestmark = pytest.mark.skipif(not shutil.which("git"), reason="needs git")


def run(folder: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], capture_output=True, text=True, check=True).stdout.strip()


def commit(folder: Path, name: str, text: str) -> str:
    (folder / name).write_text(text, encoding="utf-8")
    run(folder, "add", name)
    run(folder, "commit", "-q", "-m", name)
    return run(folder, "rev-parse", "HEAD")


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """An origin with a release v1.0.1 ahead of a clone made at v1.0.0."""
    monkeypatch.setattr(installer, "LOG", tmp_path / "install.log")
    origin, here = tmp_path / "origin", tmp_path / "clone"
    origin.mkdir()
    run(origin, "init", "-q", "-b", "master")
    commit(origin, "app.txt", "1.0.0")
    run(origin, "tag", "v1.0.0")
    subprocess.run(["git", "clone", "-q", str(origin), str(here)], check=True)
    commit(origin, "app.txt", "1.0.1")
    run(origin, "tag", "v1.0.1")
    return origin, here


def test_the_clone_moves_to_the_release_and_keeps_its_own_changes(clone: Any) -> None:
    origin, here = clone
    (here / "notes.txt").write_text("mine", encoding="utf-8")  # not tracked: left alone
    assert source_updater.move(here, "v1.0.1")
    assert (here / "app.txt").read_text(encoding="utf-8") == "1.0.1"
    assert run(here, "rev-parse", "HEAD") == run(origin, "rev-parse", "v1.0.1")
    assert (here / "notes.txt").read_text(encoding="utf-8") == "mine"
    assert source_updater.move(here, "v1.0.1")  # already there: nothing to do


def test_a_clone_with_commits_of_its_own_is_left_as_it_is(clone: Any) -> None:
    _origin, here = clone
    mine = commit(here, "mine.txt", "a change of my own")
    assert not source_updater.move(here, "v1.0.1")
    assert run(here, "rev-parse", "HEAD") == mine


def test_libraries_that_fail_put_the_code_back(
        clone: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _origin, here = clone
    before = run(here, "rev-parse", "HEAD")
    monkeypatch.setattr(source_updater.shutil, "which", lambda _name: "uv")
    monkeypatch.setattr(source_updater, "libraries", lambda *_args: 1)
    assert "could not be installed" in source_updater.update(here, "v1.0.1", "env")
    assert run(here, "rev-parse", "HEAD") == before


def test_every_library_off_its_tested_version_is_moved(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "tarjim").mkdir()
    constraints = tmp_path / "tarjim" / "constraints.txt"
    constraints.write_text("numpy==2.4.6 ; python_version >= '3.10'\nnumpy==1.26.4 ; sys_platform"
                           " == 'darwin'\nStarlette==1.10.0\nscipy==1.17.1\n", encoding="utf-8")
    listed = [{"name": "numpy", "version": "1.26.4"}, {"name": "starlette", "version": "1.9.0"},
              {"name": "scipy", "version": "1.17.1"}, {"name": "torch", "version": "2.14.1"},
              {"name": "tarjim", "version": "1.0.37"}]
    installs: list[list[str]] = []

    def uv(command: list[str], **_options: Any) -> Any:
        return SimpleNamespace(stdout=json.dumps(listed), returncode=0)

    monkeypatch.setattr(source_updater.subprocess, "run", uv)
    monkeypatch.setattr(installer, "run_install", lambda c: installs.append(c) or 0)
    assert source_updater.libraries("uv", tmp_path, "env") == 0
    assert installs[0][-2:] == ["-e", str(tmp_path)] and "-c" in installs[0]
    assert installs[1][-1:] == ["starlette"]  # numpy 1.26.4 is the tested one on a Mac


def test_the_updater_runs_from_its_copy_outside_the_engine(tmp_path: Path) -> None:
    for module in (installer, source_updater, __import__("tarjim.release_pins").release_pins):
        shutil.copyfile(str(module.__file__), tmp_path / Path(str(module.__file__)).name)
    done = subprocess.run([sys.executable, "-E", "-S", str(tmp_path / "source_updater.py"),
                           "--help"], capture_output=True, text=True, check=False)
    assert done.returncode == 0 and "engine" in done.stdout


def test_a_clone_offers_the_update_and_hands_over_to_its_updater(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(installer, "UPDATE_STATE", tmp_path / "update.json")
    monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    monkeypatch.setattr(update.shutil, "which", lambda name: name)
    started: list[list[str]] = []
    monkeypatch.setattr(installer, "start_detached", lambda c, _log: started.append(c) or True)
    assert update.from_source() and update.can_install()  # this test runs in a clone
    assert update.start("v1.0.99", 17999)
    command = started[0]
    assert command[1:4] == ["-E", "-S", str(tmp_path / "source_updater.py")]
    assert command[4:6] == [str(update.SOURCE), "v1.0.99"]
    assert json.loads(command[7])[-2:] == ["--port", "17999"]
    assert (tmp_path / "installer.py").is_file() and (tmp_path / "release_pins.py").is_file()
