"""A translation the server runs keeps its work (sound, transcript, cues) under tarjim's own
folder, where the weekly sweep clears it, never beside the person's file. The command line
still keeps it beside the video, where the person sees it and a re-run picks it up."""
from pathlib import Path
from typing import Any

import pytest

import tarjim.pipeline
from tarjim.job import Job
from tarjim.server import __main__ as engine
from tarjim.server import housekeeping
from tarjim.server.jobs import Order, Task


def hears(seen: list[bool]) -> Any:
    """What hearing leaves in the job's cache, and whether an earlier run's work was found."""
    def run(job: Job, report: Any) -> None:
        job.claim_cache()
        seen.append((job.cache / "transcript.json").exists())
        (job.cache / "transcript.json").write_text("{}", encoding="utf-8")
        (job.cache / "audio.wav").write_bytes(b"RIFF")
    return run


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(engine, "HOME", tmp_path / "home")
    return tmp_path / "home"


def test_a_file_translated_from_chat_gets_nothing_written_beside_it(
        home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private = tmp_path / "private"
    private.mkdir()
    (private / "meeting.mp4").write_bytes(b"video")
    seen: list[bool] = []
    monkeypatch.setattr(tarjim.pipeline, "run", hears(seen))
    for _ in range(2):
        engine.perform(Task(Order(str(private / "meeting.mp4"))), tmp_path / "out")
    assert sorted(p.name for p in private.iterdir()) == ["meeting.mp4"]
    assert (home / "cache" / "meeting" / "transcript.json").is_file()
    assert seen == [False, True]


def test_the_weekly_sweep_covers_the_server_work_folder(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    swept: list[list[Path]] = []
    monkeypatch.setattr(housekeeping, "sweep", swept.append)
    monkeypatch.setattr("tarjim.phone.service.service.begin", lambda *_args: None)
    monkeypatch.setattr("tarjim.server.update_routes.watch", lambda *_args: None)
    monkeypatch.setattr("tarjim.server.link_upgrade.refresh", lambda: None)
    engine.run_alongside(0)
    assert home / "cache" in swept[0]


def test_the_command_line_keeps_its_work_beside_the_video(tmp_path: Path) -> None:
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"video")
    assert Job(video).cache == tmp_path / ".tarjim" / "talk"
