"""The record of stretches asked about again (listen/kept.py), 2026-11-08: a gap inside sound heard
already is answered from it even when it moved a little, a miss beside a stretch asked in the same
job does not use up a try of a later run, and only an answer counts as a try: a request that failed
leaves the stretch to be asked again, so speech is not given up because an engine was busy."""
from pathlib import Path

import pytest
from test_coverage_flow import SPOKEN, Engine, setup

from tarjim import config, hearing
from tarjim.listen.coverage import Gap, Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import Asked
from tarjim.listen.merge import Heard
from tarjim.listen.novel import Again, WordMender
from tarjim.listen.repair import Mender


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def recorder(calls: list[tuple[float, float]]) -> object:
    def relisten(start: float, end: float) -> list[Utterance]:
        calls.append((start, end))
        return [Utterance(start + 0.5, end - 0.5, "S1", "said here")]

    return relisten


def test_a_gap_moved_a_little_inside_sound_heard_already_is_not_paid_again(
        tmp_path: Path) -> None:
    calls: list[tuple[float, float]] = []
    asked = Asked.load(tmp_path)
    again = asked.asking(recorder(calls))  # type: ignore[arg-type]
    again(20.0, 22.0)
    assert again(19.8, 22.2) and calls == [(19.25, 22.75)]
    assert asked.tries == [[19.25, 22.75, 1]]


def test_the_lines_check_and_a_words_check_found_a_little_apart_pay_once(
        tmp_path: Path) -> None:
    calls: list[tuple[float, float]] = []
    again = Asked.load(tmp_path).asking(recorder(calls))  # type: ignore[arg-type]
    hearing_ = Hearing([Utterance(0.0, 19.0, "S1", "before")], [], [])
    Mender(hearing_, again, "x").mend([Gap(20.0, 22.0, 2.0, [])])
    words = WordMender(hearing_, Again(again, "x", []), [])
    assert words.mend([Gap(19.8, 22.2, 2.4, [])]).added and len(calls) == 1


def test_a_miss_beside_a_stretch_asked_in_this_job_does_not_use_up_a_try(
        tmp_path: Path) -> None:
    calls: list[tuple[float, float]] = []
    asked = Asked.load(tmp_path)
    again = asked.asking(recorder(calls))  # type: ignore[arg-type]
    again(20.0, 22.0)
    again(19.0, 23.0)  # more sound than was heard: asked, but the same stretch
    asked.save()
    assert len(calls) == 2 and asked.tries == [[19.25, 22.75, 1]]
    assert Asked.load(tmp_path).asking(recorder(calls))(20.0, 22.0)  # type: ignore[operator]


def test_a_failed_request_is_not_a_try(tmp_path: Path) -> None:
    def busy(_start: float, _end: float) -> list[Utterance]:
        raise RuntimeError("500: busy")

    for _run in range(3):
        asked = Asked.load(tmp_path)
        with pytest.raises(RuntimeError):
            asked.asking(busy)(20.0, 22.0)
        asked.save()
    calls: list[tuple[float, float]] = []
    assert Asked.load(tmp_path).asking(recorder(calls))(20.0, 22.0)  # type: ignore[operator]
    assert calls == [(19.25, 22.75)]


def test_speech_left_out_while_the_engine_was_busy_is_filled_once_it_is_back(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0], again_fails=True)
    job = setup(monkeypatch, tmp_path, engine, local=None)
    for _run in range(3):
        hearing.transcript_for(job, lambda _stage: None)
        assert not (job.cache / "transcript.json").exists()
    engine.again_fails, engine.asked = False, 0
    transcript = hearing.transcript_for(job, lambda _stage: None)
    assert engine.asked >= 1 and max(w.end for w in transcript.words) > 235.0
    assert (job.cache / "transcript.json").exists()


class Deaf(Engine):
    """Answers when asked again, and hears nothing there."""

    def hear_slice(self, sound: bytes) -> Heard:
        self.asked += 1
        return Heard("English", [], [[]])


def test_speech_an_engine_answered_twice_with_nothing_is_not_asked_again(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Deaf([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine, local=None)
    for _run in range(2):
        hearing.transcript_for(job, lambda _stage: None)
        assert not (job.cache / "transcript.json").exists()
    assert engine.asked == 2
    capsys.readouterr()
    hearing.transcript_for(job, lambda _stage: None)
    assert "heard by no listener; not asked again" in capsys.readouterr().out
    assert engine.asked == 2 and (job.cache / "transcript.json").exists()
