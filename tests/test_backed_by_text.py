"""Which pass the audio backs most is judged by what the local listener said, all of it, not only
by the words the sound confirmed where they are timed (2026-11-09). The bench's Arabic news
read lost its last 12 s of subtitles: two of three passes left the tail out, the vote dropped it,
and the one pass that heard it lost to the vote, because the local words saying the tail were
timed off and so left out of the judging, which then took the pass's tail for lines made up."""
from pathlib import Path
from typing import Any

import pytest
import soundfile

from tarjim import hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import check, settle
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.listen.opinion import backing
from tarjim.listen.placed import placed
from tarjim.models import Word
from tests.test_emissions_once import RATE, clip
from tests.test_sounded_opinion import ALPHA, BRAVO, EARLY, PILED, ears  # noqa: F401

NEWS = "welcome to the local news tonight the library opens a new reading program"
TAIL = "that was the news for today thank you for watching and goodbye"


def said(text: str, start: float, step: float = 0.4) -> list[Word]:
    return [Word(w, start + k * step, start + k * step + 0.3) for k, w in enumerate(text.split())]


def hearing_with_a_lone_tail() -> Heard:
    body, tail = Utterance(1.0, 6.0, "S1", NEWS), Utterance(20.0, 32.0, "S1", TAIL)
    return Heard("English", [body], [[body], [body], [body, tail]])


def test_a_pass_whose_tail_only_unconfirmed_local_words_say_wins_over_the_vote() -> None:
    confirmed = said(NEWS, 1.0)
    everything = [*confirmed, *said(TAIL, 9.0, 0.0)]  # the tail heard 11 s early, no length
    found = placed(hearing_with_a_lone_tail(), confirmed, 40.0, everything)
    assert [u.text for u in found.own] == [NEWS, TAIL]


def test_without_the_text_the_confirmed_words_alone_judge_as_before() -> None:
    confirmed = said(NEWS, 1.0)
    found = placed(hearing_with_a_lone_tail(), confirmed, 40.0)
    assert [u.text for u in found.own] == [NEWS]


def test_all_the_words_back_the_passes_when_the_sound_confirmed_any() -> None:
    assert backing([ALPHA, PILED, EARLY], [ALPHA]) == [ALPHA, PILED, EARLY]


def test_none_back_them_when_the_sound_confirmed_none() -> None:
    # hardly any found in the whole clip (a script the aligner barely reads, or words in the
    # wrong letters): their text is not trusted either, and the passes are judged without it
    assert backing([ALPHA, PILED, EARLY], []) == []


def test_the_timing_is_given_every_local_word_to_judge_the_passes_by(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ears: Any) -> None:  # noqa: F811
    audio = tmp_path / "a.wav"
    soundfile.write(audio, clip(), RATE, subtype="FLOAT")
    given: list[list[Word]] = []

    def settled(_job: Job, _heard: Heard, sound: settle.Sound, _o: list[Word]) -> settle.Timed:
        given.append(sound.said)
        return settle.Timed(Transcript("English", ""), True, 1.0)

    monkeypatch.setattr(settle, "settled", settled)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(hearing, "second_opinion", lambda *_a: [ALPHA, PILED, BRAVO, EARLY])
    hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, Heard("English", [], []),
                             lambda _stage: None)
    assert given == [[ALPHA, PILED, BRAVO, EARLY]]


class Seen(Exception):
    pass


def test_settle_judges_the_passes_by_the_words_said(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[list[Utterance]] = []

    def repaired(_job: Job, _heard: Heard, hearing_: Any, _asked: Any) -> None:
        told.append(hearing_.utterances)
        raise Seen

    monkeypatch.setattr(check, "repaired", repaired)
    confirmed = said(NEWS, 1.0)
    sound = settle.Sound(clip(), RATE, [], [], [*confirmed, *said(TAIL, 9.0, 0.0)])
    with pytest.raises(Seen):
        settle.settled(Job(tmp_path / "v.mp4"), hearing_with_a_lone_tail(), sound, confirmed)
    assert [u.text for u in told[0]] == [NEWS, TAIL]
