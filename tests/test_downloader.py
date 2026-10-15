"""yt-dlp keeps itself current: asked of PyPI once a day, installed into tarjim's own environment
while nothing downloads, and only when the person lets tarjim update itself."""
import sys
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, downloader, fetch, update


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(downloader, "installed", lambda: "2026.8.19")
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(downloader.shutil, "which", lambda _name: "uv")
    return tmp_path


class Reply:
    def __init__(self, body: Any, ok: bool = True) -> None:
        self.body, self.ok = body, ok

    def json(self) -> Any:
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


def pypi(monkeypatch: pytest.MonkeyPatch, body: Any, ok: bool = True) -> list[str]:
    import requests

    asked: list[str] = []

    def get(url: str, **_options: Any) -> Reply:
        asked.append(url)
        return Reply(body, ok)

    monkeypatch.setattr(requests, "get", get)
    return asked


def runs(monkeypatch: pytest.MonkeyPatch, code: int = 0) -> list[list[str]]:
    commands: list[list[str]] = []

    class Done:
        returncode, stdout, stderr = code, "", "error: no matching distribution\n"

    def run(command: list[str], **_options: Any) -> Done:
        commands.append(command)
        return Done()

    monkeypatch.setattr(downloader.subprocess, "run", run)
    return commands


@pytest.mark.parametrize(("text", "parts"), [
    ("2026.8.19", (2026, 8, 19)), ("2026.10.05", (2026, 10, 5)), ("2026.10.5.1", (2026, 10, 5, 1)),
    ("", ()), ("2026.8", ()), ("2026.8.19 ", ()), ("2026.8.19; calc", ()), ("v2026.8.19", ()),
    ("2026.8.19.dev0", ()), ("2026.8.19\n--index-url=x", ()), ("1" * 40, ()), ("2026.8.19.1.2", ()),
])
def test_only_a_plain_release_number_is_accepted(text: str, parts: tuple[int, ...]) -> None:
    assert downloader.release(text) == parts


@pytest.mark.parametrize(("found", "have", "is_newer"), [
    ("2026.10.5", "2026.8.19", True), ("2026.8.19.1", "2026.8.19", True),
    ("2026.8.19", "2026.8.19", False), ("2026.7.1", "2026.8.19", False),
    ("2026.10.5", "", False), ("", "2026.8.19", False), ("2026.10.5", "2026.9.1.dev0", False),
])
def test_only_a_higher_number_counts_as_newer(found: str, have: str, is_newer: bool) -> None:
    assert downloader.newer(found, have) is is_newer


@pytest.mark.parametrize("body", [
    {"info": {"version": "2026.10.5; rm -rf /"}}, {"info": {"version": 7}}, {"info": None},
    ["2026.10.5"], ValueError("not json"), {}, {"info": {"version": "--upgrade"}},
])
def test_a_malformed_answer_from_pypi_installs_nothing(home: Path, monkeypatch: pytest.MonkeyPatch,
                                                       body: Any) -> None:
    pypi(monkeypatch, body)
    commands = runs(monkeypatch)
    assert downloader.refresh(idle=True) == "" and commands == []


@pytest.mark.parametrize("version", ["2026.8.19", "2026.7.1"])
def test_an_equal_or_older_release_installs_nothing(home: Path, monkeypatch: pytest.MonkeyPatch,
                                                    version: str) -> None:
    pypi(monkeypatch, {"info": {"version": version}})
    commands = runs(monkeypatch)
    assert downloader.refresh(idle=True) == "" and commands == []


def test_a_newer_release_is_installed_into_tarjims_own_environment(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = pypi(monkeypatch, {"info": {"version": "2026.10.5"}})
    commands = runs(monkeypatch)
    for name in [name for name in sys.modules if name.split(".")[0] == "yt_dlp"]:
        monkeypatch.setitem(sys.modules, name, sys.modules[name])  # put back for other tests
    monkeypatch.setitem(sys.modules, "yt_dlp", sys.modules.get("yt_dlp", sys))
    assert downloader.refresh(idle=True) == "2026.10.5"
    assert asked == ["https://pypi.org/pypi/yt-dlp/json"]
    command = commands[0]
    assert command[:3] == ["uv", "pip", "install"] and command[-1] == "yt-dlp==2026.10.5"
    assert command[command.index("--python") + 1] == sys.prefix
    assert "yt_dlp" not in sys.modules  # the next download imports the new copy
    assert downloader.progress()["state"] == "done"
    assert downloader.view()["state"] == "done"


def test_pypi_is_asked_at_most_once_a_day(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = pypi(monkeypatch, {"info": {"version": "2026.8.19"}})
    runs(monkeypatch)
    downloader.refresh(idle=True, now=1_000_000.0)
    downloader.refresh(idle=True, now=1_000_000.0 + 3600)
    assert len(asked) == 1
    downloader.refresh(idle=True, now=1_000_000.0 + 25 * 3600)
    assert len(asked) == 2


def test_a_failed_install_keeps_the_old_copy_and_is_recorded_and_not_retried_every_hour(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pypi(monkeypatch, {"info": {"version": "2026.10.5"}})
    commands = runs(monkeypatch, code=2)
    assert downloader.refresh(idle=True, now=1_000_000.0) == ""
    state = downloader.progress()
    assert state["state"] == "failed" and "no matching distribution" in state["detail"]
    assert state["version"] == "2026.10.5"
    assert downloader.refresh(idle=True, now=1_000_000.0 + 3600) == "" and len(commands) == 1
    assert update.view()["downloader"]["state"] == "failed"


@pytest.mark.parametrize("why", ["automatic off", "source copy", "job running", "in use"])
def test_nothing_is_asked_or_installed_unless_allowed_and_idle(
        home: Path, monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    asked = pypi(monkeypatch, {"info": {"version": "2026.10.5"}})
    commands = runs(monkeypatch)
    if why == "automatic off":
        config.save("auto_update", "no")
    if why == "source copy":
        monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    if why == "in use":
        fetch.IN_USE.acquire()
    try:
        assert downloader.refresh(idle=why != "job running") == ""
    finally:
        if why == "in use":
            fetch.IN_USE.release()
    assert commands == []
    if why in ("automatic off", "source copy", "job running"):
        assert asked == []


def test_the_command_refuses_a_version_that_is_not_a_plain_release_number() -> None:
    with pytest.raises(ValueError, match="version"):
        downloader.command("uv", "2026.10.5 --index-url https://example.com")
    assert downloader.command("uv", "2026.10.5")[-1] == "yt-dlp==2026.10.5"
