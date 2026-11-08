"""Each job counts its guards from nothing, the command line's jobs too, and a line the vote leaves
out counts as a copy only when it copies a line already kept (tarjim/guards.py, 2026-11-08)."""
from pathlib import Path

import pytest

from tarjim import guards, media, pipeline
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import vote

U = Utterance


class Heard(Exception):
    pass


def test_each_job_counts_from_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def hear(_job: Job, _report: object) -> None:
        seen.append(guards.counts()["anchor.moved"])
        guards.fired("anchor.moved")
        raise Heard

    monkeypatch.setattr(pipeline, "transcript_for", hear)
    monkeypatch.setattr(media, "check_readable", lambda _video: None)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"")
    guards.fired("anchor.moved", 3)  # counted before any job, as the command line did
    for _ in range(2):
        with pytest.raises(Heard):
            pipeline.run(Job(video, cache_dir=tmp_path))
    assert seen == [0, 0]


def test_a_line_two_passes_heard_is_one_extra_and_no_copy() -> None:
    guards.reset()
    first = U(0.0, 3.0, "S1", "hello there friends and welcome back to the show")
    base = [first, U(10.0, 13.0, "S1", "this is a long line with many words in it today")]
    late = U(30.0, 32.0, "S1", "today we cook rice")
    found = vote([base, [first, late], [first, late]], agree=2)
    assert late in found
    assert guards.counts()["vote.extras"] == 1 and guards.counts()["vote.extra_dropped"] == 0
