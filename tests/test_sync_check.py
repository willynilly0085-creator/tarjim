"""The words this computer heard are used only in the clip's language, and the timing is checked
against the sound, timed again without them when too few words are found where they sit."""
from pathlib import Path

import numpy as np
import pytest

from tarjim.asr import agree
from tarjim.asr.base import Transcript
from tarjim.listen import settle
from tarjim.listen.opinion import agreeing
from tarjim.models import Word

SAID = [Word("Hello", 0.0, 0.4), Word("there", 0.4, 0.8)]


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


def timed(agreement: float | None) -> settle.Timed:
    return settle.Timed(Transcript("Somali", "x"), True, agreement)


# Changed 2026-11-08: the speech left out is now filled once before either timing
# (settle.settled), so the choice between the two timings is tested on its own here.
def test_a_timing_off_the_voice_is_made_again_on_the_sound_alone() -> None:
    asked: list[bool] = []
    done = settle.better(timed(0.1), lambda: asked.append(True) or timed(0.9), True)
    assert asked == [True] and done.agreement == 0.9


@pytest.mark.parametrize(("agreements", "second", "times"), [
    ([0.95], True, 0),  # in time: no second try
    ([0.1], False, 0),  # no second opinion was used: nothing else to try
    ([None], True, 0),  # cannot be told: kept
    ([0.4, 0.3], True, 1),  # the second try is worse: the first stays
])
def test_a_timing_is_tried_again_only_when_that_can_help(
        agreements: list[float | None], second: bool, times: int) -> None:
    asked: list[bool] = []
    done = settle.better(timed(agreements[0]),
                         lambda: asked.append(True) or timed(agreements[-1]), second)
    assert len(asked) == times and done.agreement == agreements[0]


def test_the_local_words_of_another_language_never_reach_the_timing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import hearing

    monkeypatch.setattr(hearing, "qwen_transcript", lambda _a: Transcript("Arabic", "x", SAID))
    assert hearing.second_opinion(Path("a.wav"), "Somali") == []
    assert hearing.second_opinion(Path("a.wav"), "Arabic") == SAID
