"""A stretch whose local words were left out as unconfirmed is not one the local listener heard
nothing in: it stays open, as with the local listener off (2026-11-08 review of A1)."""
from pathlib import Path
from typing import Any

import pytest
import soundfile

from tarjim import hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import check, settle
from tarjim.listen.coverage import NOT_REPAIRED, Gap, Hearing
from tarjim.listen.merge import Heard
from tarjim.listen.opinion import doubted
from tarjim.listen.repair import Mender
from tarjim.models import Word
from tests.test_emissions_once import RATE, clip
from tests.test_sounded_opinion import ALPHA, BRAVO, EARLY, PILED, ears  # noqa: F401

FAR = [Word("far", 100.0, 100.3)]  # a confirmed local word, nowhere near the gap
GAP = Gap(10.0, 15.0, 5.0, [])


def outcome(local: list[Word], doubts: list[tuple[float, float]]) -> str:
    mender = Mender(Hearing([], local, [(10.0, 15.0)], doubts), lambda _a, _b: [], "x")
    return mender.fill(GAP, [])[1]


def test_a_gap_with_no_local_words_at_all_is_left_as_it_is() -> None:
    assert "no listener heard words here" in outcome(FAR, [])


def test_a_gap_whose_local_words_were_left_out_stays_open() -> None:
    assert outcome(FAR, [(11.0, 11.4)]) == NOT_REPAIRED


def test_left_out_words_timed_a_drift_away_keep_it_open_too() -> None:
    assert outcome(FAR, [(1.0, 1.4)]) == NOT_REPAIRED  # 9 s early, as on the Arabic bench
    assert "no listener heard words here" in outcome(FAR, [(40.0, 40.4)])


def test_the_words_left_out_are_where_the_sound_did_not_confirm_them() -> None:
    assert doubted([ALPHA, PILED, BRAVO, EARLY], [ALPHA, BRAVO]) == [(3.3, 3.3), (12.0, 12.3)]


def test_the_timing_is_told_where_the_words_left_out_were(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ears: Any) -> None:  # noqa: F811
    audio = tmp_path / "a.wav"
    soundfile.write(audio, clip(), RATE, subtype="FLOAT")
    given: list[list[tuple[float, float]]] = []

    def settled(_job: Job, _heard: Heard, sound: settle.Sound, _o: list[Word]) -> settle.Timed:
        given.append(sound.doubted)
        return settle.Timed(Transcript("English", ""), True, 1.0)

    monkeypatch.setattr(settle, "settled", settled)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(hearing, "second_opinion", lambda *_a: [ALPHA, PILED, BRAVO, EARLY])
    heard = Heard("English", [], [])
    hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, heard, lambda _stage: None)
    assert given == [[(3.3, 3.3), (12.0, 12.3)]]


class Seen(Exception):
    pass


def test_the_coverage_check_is_told_where_the_words_left_out_were(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[Hearing] = []

    def repaired(_job: Job, _heard: Heard, hearing_: Hearing, _asked: Any) -> None:
        told.append(hearing_)
        raise Seen

    monkeypatch.setattr(check, "repaired", repaired)
    sound = settle.Sound(clip(), RATE, [(0.0, 1.0)], [(11.0, 11.4)])
    with pytest.raises(Seen):
        settle.settled(Job(tmp_path / "v.mp4"), Heard("English", [], []), sound, FAR)
    assert told[0].doubted == [(11.0, 11.4)] and told[0].local == FAR
