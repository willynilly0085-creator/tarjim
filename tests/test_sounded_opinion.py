"""Before anything uses the words this computer heard, they are looked for in the letters the
aligner heard in the whole clip once, the letters timing reads too; what is left out is said once
in the log and counted (listen/opinion.sounded, 2026-11-08)."""
from pathlib import Path
from typing import Any

import pytest
import soundfile

from tarjim import guards, hearing
from tarjim.asr import align
from tarjim.asr.align import AlignEngine
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import check, settle
from tarjim.listen.merge import Heard
from tarjim.listen.opinion import sounded
from tarjim.listen.timing import Timer
from tarjim.models import Word
from tests.test_emissions_once import RATE, SECONDS, Emitter, Hearing, Roman, clip

ALPHA = Word("alpha", 3.0, 3.3)  # said there (tests/test_emissions_once.SAID)
BRAVO = Word("bravo", 25.0, 25.3)
EARLY = Word("bravo", 12.0, 12.3)  # 13 s before it is said, on silence
PILED = Word("alpha", 3.3, 3.3)


@pytest.fixture
def ears(monkeypatch: pytest.MonkeyPatch) -> Hearing:
    heard = Hearing()
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(heard), Roman()  # type: ignore[assignment]
    monkeypatch.setattr(align, "shared_aligner", lambda: engine)
    guards.reset()
    return heard


def test_the_local_words_are_looked_for_in_the_letters_timing_reads_too(
        ears: Hearing, capsys: pytest.CaptureFixture[str]) -> None:
    wav = clip()
    kept = sounded([ALPHA, PILED, BRAVO, EARLY], wav)
    assert kept == [ALPHA, BRAVO]
    assert Timer(wav, RATE, "English", kept).agreement(kept) == 1.0
    assert ears.passes == [SECONDS]  # one hearing of the clip for both
    lines = [line for line in capsys.readouterr().out.splitlines() if "this computer" in line]
    assert len(lines) == 1 and "4 words" in lines[0] and "2 are used" in lines[0]
    counts = guards.counts()
    assert counts["opinion.no_length"] == 1 and counts["opinion.not_found"] == 1


def test_hardly_any_found_and_none_is_used_is_said_and_counted(
        ears: Hearing, capsys: pytest.CaptureFixture[str]) -> None:
    timed = [Word("alpha", 30.0 + k, 30.3 + k) for k in (0, 2, 4)]
    assert sounded(timed, clip()) == []
    assert "none is used" in capsys.readouterr().out
    assert guards.counts()["opinion.unused"] == 3


def test_no_words_hears_nothing(ears: Hearing) -> None:
    assert sounded([], clip()) == [] and ears.passes == []


def test_a_stand_in_aligner_with_no_ears_leaves_the_words_with_a_length(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(align, "shared_aligner", object)
    assert sounded([ALPHA, PILED, EARLY], clip()) == [ALPHA, EARLY]


def test_the_lines_are_timed_with_only_the_words_the_sound_confirms(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ears: Hearing) -> None:
    audio = tmp_path / "a.wav"
    soundfile.write(audio, clip(), RATE, subtype="FLOAT")
    given: list[list[Word]] = []

    def settled(_job: Job, _heard: Heard, _sound: Any, opinion: list[Word]) -> settle.Timed:
        given.append(opinion)
        return settle.Timed(Transcript("English", ""), True, 1.0)

    monkeypatch.setattr(settle, "settled", settled)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(hearing, "second_opinion", lambda *_a: [ALPHA, PILED, BRAVO, EARLY])
    heard = Heard("English", [], [])
    hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, heard, lambda _stage: None)
    assert given == [[ALPHA, BRAVO]]
