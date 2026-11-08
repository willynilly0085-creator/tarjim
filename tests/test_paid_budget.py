"""One budget a job for the stretches asked about again (2026-11-08): requests and seconds of
sound, lower on a subscription. A stretch the budget refuses, a request that failed and a used-up
quota leave the stretch open, whatever the local words say: it is listed, the transcript is not
kept, and the next run asks it. Before, with the local listener on, such a stretch vanished."""
import json
from pathlib import Path

import pytest
from test_coverage_flow import LOCAL, SPOKEN, Engine, setup

from tarjim import config, hearing
from tarjim.findings import FINDINGS, Findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.job import Job
from tarjim.listen import budget
from tarjim.listen.asked import Asked
from tarjim.listen.budget import Budget, Refused, budget_for
from tarjim.listen.coverage import NOT_REPAIRED, Gap, Hearing, open_gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import DERIVE, keep_heard
from tarjim.listen.merge import Heard
from tarjim.listen.repair import Mender
from tarjim.listen.settle import worth_keeping
from tarjim.models import Word


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


class Counting:
    """A paid listener asked about a stretch: what it was asked, and a line heard there."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[float, float]] = []
        self.error = error

    def __call__(self, start: float, end: float) -> list[Utterance]:
        self.calls.append((start, end))
        if self.error is not None:
            raise self.error
        return [Utterance(start + 0.75, end - 0.75, "S1", f"new {start:.0f}")]


def twenty_gaps() -> list[Gap]:
    return [Gap(5.0 * k + 1.0, 5.0 * k + 3.0, 2.0, []) for k in range(20)]  # a 2-minute clip


def test_the_budget_follows_the_clip_and_the_engine() -> None:
    two = budget_for("gemini", 120.0)
    assert (two.requests, two.audio, two.passes) == (9, 180.0, 3)
    long = budget_for("gemini", 30 * 60.0)
    assert long.requests == 33 and long.audio == pytest.approx(540.0)
    assert budget_for("antigravity", 120.0).requests == 5  # half, on the subscription
    assert budget_for("openai", 120.0).audio == 60.0  # one pass a request


def test_a_two_minute_clip_with_twenty_gaps_sends_at_most_the_budget(tmp_path: Path) -> None:
    asked, paid = Asked.load(tmp_path, budget_for("gemini", 120.0)), Counting()
    mended = Mender(Hearing([], [], []), asked.asking(paid), "x").mend(twenty_gaps())
    assert len(paid.calls) == 9 and len(asked.budget.refused) == 11
    assert len(mended.left) == 11 and open_gaps(mended.left) == mended.left
    assert not worth_keeping(mended.left)
    asked.save()  # a refusal is no try
    assert len(json.loads((tmp_path / "asked.json").read_text(encoding="utf-8"))["asked"]) == 9
    again, more = Asked.load(tmp_path, budget_for("gemini", 120.0)), Counting()
    Mender(Hearing([], [], []), again.asking(more), "x").mend(mended.left)
    assert len(more.calls) == 9  # the next run asks the refused stretches


def test_the_seconds_of_sound_are_capped_too(tmp_path: Path) -> None:
    asked, paid = Asked.load(tmp_path, budget_for("gemini", 120.0)), Counting()
    once = asked.asking(paid)
    once(0.0, 70.0)  # the first stretch of a job is heard whole, however long
    with pytest.raises(Refused):
        once(80.0, 90.0)
    assert len(paid.calls) == 1 and asked.budget.refused == [(79.25, 90.75)]


def test_an_answer_from_sound_heard_already_is_free(tmp_path: Path) -> None:
    asked, paid = Asked.load(tmp_path, Budget(1, 1000.0, 3)), Counting()
    once = asked.asking(paid)
    once(10.0, 20.0)
    assert once(12.0, 15.0) is not None and asked.budget.made == 1 and len(paid.calls) == 1


def test_after_a_used_up_quota_nothing_is_asked(tmp_path: Path) -> None:
    asked = Asked.load(tmp_path, budget_for("gemini", 120.0))
    paid = Counting(QuotaExhausted("Gemini free quota is used up for today on every model"))
    mended = Mender(Hearing([], [], []), asked.asking(paid), "x").mend(twenty_gaps())
    assert len(paid.calls) == 1 and asked.exhausted and asked.budget.refused == []
    assert len(open_gaps(mended.left)) == 20


@pytest.mark.parametrize("error", [Refused("over budget"), RuntimeError("500: busy"),
                                   QuotaExhausted("quota")], ids=["refused", "failed", "quota"])
def test_an_unasked_stretch_stays_open_whatever_the_local_words_say(error: Exception) -> None:
    line = Utterance(0.0, 9.0, "S1", "alpha beta gamma delta")
    local = [Word("elsewhere", 40.0, 40.5)]  # the local listener ran, and heard nothing here
    mender = Mender(Hearing([line], local, []), Counting(error), "x")
    assert mender.fill(Gap(20.0, 23.0, 3.0, []), [line]) == ([], NOT_REPAIRED)
    repeated = [Word(w, 10.0 + k * 0.4, 10.3 + k * 0.4) for k, w in enumerate(line.text.split())]
    assert mender.fill(Gap(10.0, 12.0, 2.0, repeated), [line]) == ([], NOT_REPAIRED)
    left = mender.mend([Gap(20.0, 23.0, 3.0, [])]).left
    assert open_gaps(left) == left and not worth_keeping(left)


def run(job: Job) -> Findings:
    record = Findings()
    token = FINDINGS.set(record)
    try:
        hearing.transcript_for(job, lambda _stage: None)
    finally:
        FINDINGS.reset(token)
    return record


def test_with_the_local_listener_a_refused_stretch_is_listed_and_asked_next_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    local = [w for w in LOCAL if w.start < 160.0]  # it ran, and missed the end
    job = setup(monkeypatch, tmp_path, engine, local=local)
    real = budget.budget_for
    monkeypatch.setattr(budget, "budget_for", lambda *_a: Budget(0, 0.0, 3))
    refused = run(job)
    assert engine.asked == 0 and refused.left and not (job.cache / "transcript.json").exists()
    [note] = [n for n in refused.notes([], []) if n["kind"] == "budget_used"]
    assert not note["problem"] and note["at"][0] == pytest.approx(161.25, abs=1.0)
    monkeypatch.setattr(budget, "budget_for", real)
    asked = run(job)
    assert engine.asked == 1 and not asked.left and (job.cache / "transcript.json").exists()


def test_a_used_up_quota_stops_every_later_ask_in_the_job(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Spent(Engine):
        def hear_slice(self, sound: bytes) -> Heard:
            self.asked += 1
            raise QuotaExhausted("Gemini free quota is used up for today on every model")

    engine = Spent([u for u in SPOKEN if not 60.0 <= u.start < 90.0 and u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine, local=None)
    assert len(run(job).left) == 2 and engine.asked == 1


def test_asks_made_because_the_transcript_is_derived_again_say_so(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    first = [u for u in SPOKEN if u.start < 160.0]
    engine = Engine(first)
    job = setup(monkeypatch, tmp_path, engine)
    job.cache.mkdir(parents=True, exist_ok=True)
    keep_heard(job.cache, Heard("English", first, [first], provider="fakecloud"))
    stale = {DERIVE: "older code", "language": "English", "text": "", "words": []}
    (job.cache / "transcript.json").write_text(json.dumps(stale), encoding="utf-8")
    hearing.transcript_for(job, lambda _stage: None)
    log = capsys.readouterr().out
    assert engine.asked == 1 and "paid ask 1 of 9" in log
    assert "because the kept transcript is derived again" in log

