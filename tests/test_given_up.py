"""Speech asked about TRIES times with nothing heard is given up but stays listed (2026-11-08):
the transcript is kept, and the job, and every later run from the kept transcript, still shows
the speech that has no words, where before the job showed plain success."""
from pathlib import Path

import pytest
from test_asked_ledger import Deaf
from test_coverage_flow import SPOKEN, setup

from tarjim import config, hearing
from tarjim.findings import FINDINGS, Findings
from tarjim.job import Job


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def run(job: Job) -> Findings:
    """One job, with its own record."""
    record = Findings()
    token = FINDINGS.set(record)
    try:
        hearing.transcript_for(job, lambda _stage: None)
    finally:
        FINDINGS.reset(token)
    return record


def test_speech_given_up_stays_listed_and_the_transcript_is_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Deaf([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine, local=None)
    for _run in range(2):
        asked = run(job)
        assert asked.left and not asked.given_up
        assert not (job.cache / "transcript.json").exists()
    spent = run(job)
    assert spent.left == [] and spent.given_up and (job.cache / "transcript.json").exists()
    assert spent.given_up[0][0] == pytest.approx(162.0, abs=1.0)
    again = run(job)  # from the kept transcript
    assert again.given_up == spent.given_up and engine.asked == 2
    [left] = [n for n in again.notes([], []) if n["kind"] == "speech_left"]
    assert left["problem"] and left["count"] == len(spent.given_up)
