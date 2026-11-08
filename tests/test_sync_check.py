"""The words this computer heard are used only in the clip's language, and the timing is checked
against the sound, timed again without them when too few words are found where they sit."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tarjim.asr import agree
from tarjim.asr.base import Transcript
from tarjim.listen import settle
from tarjim.listen.merge import Heard
from tarjim.listen.opinion import agreeing
from tarjim.models import Word

SAID = [Word("Hello", 0.0, 0.4), Word("there", 0.4, 0.8)]
HEARD = Heard("Somali", [], [])


def test_words_in_another_language_than_the_one_heard_are_not_used() -> None:
    assert agreeing(SAID, "Arabic", "Somali") == []
    assert agreeing(SAID, "English,Arabic", "English") == SAID
    assert agreeing(SAID, "english", "English") == SAID
    assert agreeing(SAID, "", "Somali") == SAID  # nothing heard here to compare
    assert agreeing(SAID, "Arabic", "") == SAID


def test_words_said_close_together_by_one_speaker_make_one_run() -> None:
    words = [Word("a", 0.0, 0.3, "S1"), Word("b", 0.4, 0.6, "S1"), Word("c", 2.0, 2.3, "S1"),
             Word("d", 2.4, 2.6, "S2")]
    assert [[w.text for w in run] for run in agree.runs(words)] == [["a", "b"], ["c"], ["d"]]


def letters_at(frames: int, said: dict[int, range]) -> np.ndarray:
    """Log-likelihoods where each letter is heard only over its own frames."""
    logp = np.full((frames, 8), np.log(1e-4))
    logp[:, 0] = np.log(0.9)  # the blank, everywhere else
    for token, where in said.items():
        logp[where, token], logp[where, 0] = np.log(0.95), np.log(1e-4)
    return logp


def test_words_are_found_only_where_they_are_said() -> None:
    logp = letters_at(500, {5: range(50, 60), 6: range(60, 70)})  # 1.0-1.4 s
    tokens = {"ab": [5, 6], "zz": [7]}.get

    def found(start: float, end: float, text: str) -> float | None:
        return agree.agreement(logp, [Word(text, start, end)], lambda t: tokens(t, []))

    assert found(1.0, 1.4, "ab") == 1.0
    assert found(6.0, 6.4, "ab") == 0.0  # the same words twenty seconds late
    assert found(1.0, 1.4, "12") is None  # no letters to look for


def timing(agreements: list[float | None]) -> tuple[list[list[Word]], Any]:
    asked: list[list[Word]] = []

    def timed(_job: Any, _heard: Any, _sound: Any, opinion: list[Word]) -> settle.Timed:
        asked.append(opinion)
        return settle.Timed(Transcript("Somali", "x"), True, agreements[len(asked) - 1])

    return asked, timed


def test_a_timing_off_the_voice_is_made_again_on_the_sound_alone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    asked, timed = timing([0.1, 0.9])
    monkeypatch.setattr(settle, "timed", timed)
    sound = settle.Sound(None, 16000, [])
    done = settle.settled(None, HEARD, sound, SAID)  # type: ignore[arg-type]
    assert asked == [SAID, []] and done.agreement == 0.9


@pytest.mark.parametrize(("agreements", "opinion", "times"), [
    ([0.95], SAID, 1),  # in time: no second try
    ([0.1], [], 1),  # no second opinion was used: nothing else to try
    ([None], SAID, 1),  # cannot be told: kept
    ([0.4, 0.3], SAID, 2),  # the second try is worse: the first stays
])
def test_a_timing_is_tried_again_only_when_that_can_help(
        monkeypatch: pytest.MonkeyPatch, agreements: list[float | None], opinion: list[Word],
        times: int) -> None:
    asked, timed = timing(agreements)
    monkeypatch.setattr(settle, "timed", timed)
    done = settle.settled(None, HEARD, settle.Sound(None, 1, []), opinion)  # type: ignore[arg-type]
    assert len(asked) == times and done.agreement == agreements[0]


def test_the_local_words_of_another_language_never_reach_the_timing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import hearing

    monkeypatch.setattr(hearing, "qwen_transcript", lambda _a: Transcript("Arabic", "x", SAID))
    assert hearing.second_opinion(Path("a.wav"), "Somali") == []
    assert hearing.second_opinion(Path("a.wav"), "Arabic") == SAID
