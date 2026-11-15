"""Reading a link's qualities always ends. On 2026-11-15 the phone bot stayed on "reading the
qualities" for good: the engine had been started in Windows' system folder, yt-dlp tested a
YouTube format and keeps the test's temporary file in the current folder, nothing can be
written there, and Python's tempfile tries a folder it cannot write to two thousand million
times. The same read from a folder that can be written took 3 seconds."""
import os
import tempfile
import threading
from pathlib import Path

import pytest
from yt_dlp import YoutubeDL

from tarjim import fetch
from tarjim.server import boot


def test_yt_dlp_keeps_its_temporary_files_in_the_temporary_folder(tmp_path: Path) -> None:
    for asked in (fetch.asking(), fetch.options(tmp_path)):
        with YoutubeDL(asked) as ydl:
            kept = Path(ydl.get_output_path("temp"))
        assert kept.is_absolute() and kept == Path(tempfile.gettempdir())


def test_the_engine_works_from_its_own_folder_wherever_it_was_started(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started, home = tmp_path / "system", tmp_path / "home"
    started.mkdir()
    monkeypatch.chdir(started)
    monkeypatch.setenv("TARJIM_HOME", str(home))
    boot.settle()
    assert Path.cwd() == home


def test_an_engine_that_cannot_enter_its_folder_still_starts(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TARJIM_HOME", str(tmp_path / "home"))

    def refused(_folder: object) -> None:
        raise PermissionError("no")

    monkeypatch.setattr(os, "chdir", refused)
    boot.settle()


def test_a_read_that_never_returns_is_given_up(monkeypatch: pytest.MonkeyPatch) -> None:
    held = threading.Event()
    monkeypatch.setattr(fetch, "looked", lambda _url: held.wait(30))
    monkeypatch.setattr(fetch, "LOOK_SECONDS", 0.2)
    try:
        with pytest.raises(TimeoutError):
            fetch.look("https://example.com/v")
    finally:
        held.set()


def test_a_read_that_fails_says_its_own_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(_url: str) -> None:
        raise RuntimeError("the site refused")

    monkeypatch.setattr(fetch, "looked", refused)
    with pytest.raises(RuntimeError, match="the site refused"):
        fetch.look("https://example.com/v")


def test_a_read_in_time_is_what_was_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "looked", lambda url: {"title": url})
    assert fetch.look("https://example.com/v") == {"title": "https://example.com/v"}
