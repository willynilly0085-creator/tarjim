"""A stretch of speech the cloud listener left out is filled with every local word said in it
that confirmed words either side hold in place, not only with the confirmed ones (2026-11-09).

Since A1 (2026-11-08) a fill took only the words the sound confirmed, so its text had holes: in
the bench's en_long_three_pieces "rails, like a drawer. The first" (a run scoring under the clip's
bar) and two "a" with no length were left out of a 9 s stretch, and in en_long_seven "a picture of
the moon." at a stretch's end; their subtitles went missing. The listener says its words in order,
so words between two it said where the sound confirms them were said between those two; when
their own times leave little more room than that, the stretch is theirs. Words with no kept word
on one side, or with room for a drift, stay out, as A1 meant."""
from pathlib import Path
from typing import Any

import pytest
import soundfile

from tarjim import hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import check, settle
from tarjim.listen.coverage import Hearing, gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.listen.opinion import held
from tarjim.models import Word
from tests.test_emissions_once import RATE, clip
from tests.test_sounded_opinion import ALPHA, BRAVO, EARLY, PILED, ears  # noqa: F401

LINE = Utterance(0.0, 10.0, "S1", "one two three four five")


def said(text: str, start: float, step: float = 0.4) -> list[Word]:
    return [Word(w, start + k * step, start + k * step + 0.3) for k, w in enumerate(text.split())]


BEFORE = said("we built a roof that slides on", 20.0)  # 20.0-22.7
RAILS = said("rails like a drawer the first", 22.8)  # under the bar, 22.8-25.1
AFTER = said("version got stuck halfway every single", 25.2)
ALL = [*BEFORE, *RAILS, *AFTER]
KEPT = [*BEFORE, *AFTER]


def test_words_between_two_kept_ones_are_held_in_place() -> None:
    assert held(ALL, KEPT) == ALL


def test_a_word_with_no_length_between_kept_ones_is_held() -> None:
    lone = Word("a", 22.75, 22.75)
    assert held([*BEFORE, lone, *RAILS], [*BEFORE, *RAILS]) == [*BEFORE, lone, *RAILS]


def test_words_past_the_last_kept_one_are_not_held() -> None:
    assert held([*BEFORE, *RAILS], BEFORE) == BEFORE


def test_words_with_room_for_a_drift_between_the_kept_ones_are_not_held() -> None:
    late = said("version got stuck halfway every single", 29.0)  # 3.8 s past the words between
    assert held([*BEFORE, *RAILS, *late], [*BEFORE, *late]) == [*BEFORE, *late]


def test_nothing_is_held_when_none_was_kept() -> None:
    assert held(ALL, []) == []


def test_a_gap_is_filled_with_the_held_words() -> None:
    hearing = Hearing([LINE], KEPT, [(0.0, 10.0), (20.0, 27.5)], [], held(ALL, KEPT))
    [gap] = gaps(hearing)
    assert [w.text for w in gap.words] == [w.text for w in ALL]


def test_without_held_words_a_gap_has_the_kept_ones() -> None:
    [gap] = gaps(Hearing([LINE], KEPT, [(0.0, 10.0), (20.0, 27.5)]))
    assert gap.words == KEPT


class Seen(Exception):
    pass


def test_settle_fills_with_the_held_words(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[Hearing] = []

    def repaired(_job: Job, _heard: Heard, hearing_: Hearing, _asked: Any) -> None:
        told.append(hearing_)
        raise Seen

    monkeypatch.setattr(check, "repaired", repaired)
    sound = settle.Sound(clip(), RATE, [(0.0, 1.0)], [], ALL, held(ALL, KEPT))
    with pytest.raises(Seen):
        settle.settled(Job(tmp_path / "v.mp4"), Heard("English", [], []), sound, KEPT)
    assert told[0].held == ALL and told[0].local == KEPT


def test_the_timing_is_given_the_held_words(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                            ears: Any) -> None:  # noqa: F811
    audio = tmp_path / "a.wav"
    soundfile.write(audio, clip(), RATE, subtype="FLOAT")
    given: list[list[Word]] = []

    def settled(_job: Job, _heard: Heard, sound: settle.Sound, _o: list[Word]) -> settle.Timed:
        given.append(sound.held)
        return settle.Timed(Transcript("English", ""), True, 1.0)

    monkeypatch.setattr(settle, "settled", settled)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(hearing, "second_opinion", lambda *_a: [ALPHA, PILED, BRAVO, EARLY])
    hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, Heard("English", [], []),
                             lambda _stage: None)
    # the piled and the early word leave 12 s between the kept ones: room for a drift
    assert given == [[ALPHA, BRAVO]]
