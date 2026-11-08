"""A stretch is paid for once per job and at most twice across runs, the speech left out is filled
once for both timings, the hearing kept is the chosen timing's, a timing off the voice is not kept,
and local words fill with a speaker of their own (2026-11-08)."""
import json
from pathlib import Path

import pytest
from test_coverage_flow import LOCAL, SPOKEN, Engine, everything, said, setup

from tarjim import config, hearing
from tarjim.findings import FINDINGS, Findings
from tarjim.listen import check, timing
from tarjim.listen.coverage import Gap, Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import Asked, Spent
from tarjim.listen.novel import Again, WordMender
from tarjim.listen.repair import Mender
from tarjim.models import Word


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def lines_at(start: float, end: float) -> list[Utterance]:
    return [Utterance(10.0, 12.0, "S1", "a b"), Utterance(14.0, 16.0, "S2", "c d")]


def test_a_stretch_inside_one_asked_already_is_answered_from_it(tmp_path: Path) -> None:
    calls: list[tuple[float, float]] = []

    def relisten(start: float, end: float) -> list[Utterance]:
        calls.append((start, end))
        return lines_at(start, end)

    again = Asked.load(tmp_path).asking(relisten)
    assert len(again(9.0, 17.0)) == 2  # the sound asked for is 0.75 s wider either side
    assert again(13.5, 15.0) == [Utterance(14.0, 15.75, "S2", "c d")]  # clipped to its sound
    assert again(30.0, 35.0) and calls == [(8.25, 17.75), (29.25, 35.75)]


def test_a_failed_request_is_not_made_again_in_the_same_job(tmp_path: Path) -> None:
    calls: list[float] = []

    def failing(start: float, _end: float) -> list[Utterance]:
        calls.append(start)
        raise RuntimeError("busy")

    again = Asked.load(tmp_path).asking(failing)
    with pytest.raises(RuntimeError):
        again(9.0, 17.0)
    assert again(10.0, 16.0) == [] and calls == [8.25]


def test_a_stretch_is_asked_about_twice_across_runs_at_most(tmp_path: Path) -> None:
    for start in (9.0, 9.4):  # the same stretch, found a little apart by another run
        asked = Asked.load(tmp_path)
        asked.asking(lines_at)(start, 17.0)
        asked.save()
    with pytest.raises(Spent):
        Asked.load(tmp_path).asking(lines_at)(9.2, 16.8)
    assert Asked.load(tmp_path).asking(lines_at)(40.0, 45.0)  # another stretch still is


def off_the_voice(monkeypatch: pytest.MonkeyPatch, second: float) -> list[str]:
    """Words found 10% where they are timed with the local words, `second` without them; the
    order of the timings and of the hearing being kept."""
    events: list[str] = []
    keep = check.keep_heard

    def agreement(self: timing.Timer, _words: list[Word]) -> float:
        events.append("timed")
        return 0.1 if self.opinion else second

    def kept(cache: Path, heard: object) -> None:
        events.append("kept")
        keep(cache, heard)  # type: ignore[arg-type]

    monkeypatch.setattr(timing.Timer, "agreement", agreement)
    monkeypatch.setattr(check, "keep_heard", kept)
    return events


def test_both_timings_share_one_repair_and_the_winner_is_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine)
    events = off_the_voice(monkeypatch, 0.9)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    assert "on the sound alone, 90% found" in capsys.readouterr().out
    # changed 2026-11-08: the hearing is also kept before the first timing, so a crash during
    # a long timing does not throw away a hearing that was paid for (tests/test_kept_early.py)
    assert engine.asked == 1 and events == ["kept", "timed", "timed", "kept"]
    assert said(transcript) == everything()
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert len(kept["added"]) == 13 and (job.cache / "transcript.json").exists()


def test_a_timing_found_seldom_where_it_is_placed_is_kept_with_its_share(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Changed 2026-11-08: such a timing was not kept, and every later run timed the whole clip
    again on this computer with the same result. It is kept with the share found, so a run from
    it still warns that the subtitles may not follow the voice, and nothing is timed again."""
    job = setup(monkeypatch, tmp_path, Engine(list(SPOKEN)))
    events = off_the_voice(monkeypatch, 0.05)
    found = [Findings(), Findings()]
    for record in found:  # each run is a job of its own, with its own record
        token = FINDINGS.set(record)
        try:
            hearing.transcript_for(job, lambda _stage: None)
        finally:
            FINDINGS.reset(token)
        assert (job.cache / "heard.json").exists() and (job.cache / "transcript.json").exists()
    assert [record.agreement for record in found] == [0.1, 0.1]
    assert [n["kind"] for n in found[1].notes([], [])] == ["timing"]
    assert events.count("timed") == 2  # the second run timed nothing


def test_a_missing_local_listener_is_said_once_with_why(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def missing(_audio: Path) -> object:
        raise OSError("Qwen/Qwen3-ASR is not a local folder")

    monkeypatch.setattr(hearing, "qwen_transcript", missing)
    assert hearing.second_opinion(Path("a.wav"), "English") == []
    log = capsys.readouterr().out
    assert log.count("no words from the listener on this computer") == 1
    assert "OSError: Qwen/Qwen3-ASR is not a local folder" in log


LINE = Utterance(10.0, 13.0, "S1", "alpha beta gamma delta")
HEARD_HERE = [Word(t, 10.0 + 0.7 * k, 10.5 + 0.7 * k) for k, t in enumerate(LINE.text.split())]


def word_mender(timed_at: float, relisten: object) -> WordMender:
    words = [Word(w.text, w.start - 10.0 + timed_at, w.end - 10.0 + timed_at, "S1")
             for w in HEARD_HERE]
    return WordMender(Hearing([LINE], HEARD_HERE, []), Again(relisten, "x", []),  # type: ignore[arg-type]
                      words)


def test_local_words_are_in_the_transcript_only_where_its_words_are_timed() -> None:
    gap = Gap(10.0, 13.0, 3.0, HEARD_HERE)
    here = word_mender(10.0, lambda _a, _b: [])
    assert here.fill(gap, [LINE]) == (
        [], "the local words here are already in the transcript; left as it is")
    elsewhere = word_mender(30.0, lambda _a, _b: [])
    assert elsewhere.fill(gap, [LINE]) == ([], "not repaired")


def test_local_fills_take_the_speaker_of_the_turn_they_go_on_with() -> None:
    turns = [Utterance(0.0, 5.0, "S2", "one two"), Utterance(20.0, 25.0, "S1", "three four")]
    mender = Mender(Hearing(turns, [], []), None, "x")

    def filled(start: float, lines: list[Utterance]) -> str:
        words = [Word(f"new{k}", start + 0.4 * k, start + 0.4 * k + 0.3) for k in range(4)]
        [line] = mender.fill(Gap(start, start + 1.6, 1.6, words), lines)[0]
        return line.speaker

    assert filled(5.1, turns) == "S2"  # goes straight on from the turn before
    assert filled(12.5, turns) == "S1"  # nearer the turn after
    assert filled(12.5, []) == "S1"  # no turn at all: never ""


def test_the_words_this_computer_heard_fill_a_stretch_asked_twice(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = setup(monkeypatch, tmp_path, Engine([u for u in SPOKEN if u.start < 160.0]))
    asked = Asked(job.cache / "asked.json", [[161.25, 239.75, 2]])
    job.cache.mkdir(parents=True, exist_ok=True)
    asked.save()
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    monkeypatch.setattr(hearing, "cloud_listener", engine.cloud_listener)
    transcript = hearing.transcript_for(job, lambda _stage: None)
    assert engine.asked == 0 and said(transcript) == {w.text for w in LOCAL}
