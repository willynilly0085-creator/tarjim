"""A gap is never filled with a sentence a line close by already says, and lines added far apart
are aligned each in its own stretch of sound (2026-11-08, a 410 s interview)."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import align
from tarjim.listen.coverage import Gap, Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.repair import Mender
from tarjim.listen.timing import Timer
from tarjim.models import Word

SORRY = "I apologize, Jim, if things got heated, but you did make some pretty"


def said(text: str, start: float) -> list[Word]:
    return [Word(w, start + k * 0.3, start + k * 0.3 + 0.25) for k, w in enumerate(text.split())]


def test_local_words_a_line_close_by_already_says_are_not_added() -> None:
    line = Utterance(388.7, 390.9, "S1", SORRY)
    mender = Mender(Hearing([line], [], []), None, "gemini")
    again = Gap(388.8, 391.8, 3.0, said(SORRY.partition(" ")[2], 388.8))
    # Changed 2026-11-08: lines have no word times yet, so whether the line's words are said in
    # the gap is told after alignment (tests/test_heard_once.py), not taken for granted here.
    assert mender.fill(again, [line]) == (
        [], "the local words here are said by a line close by; checked once it is timed")
    new = Gap(395.0, 398.0, 3.0, said("thank you and I will hand it over to Sarah", 395.0))
    assert [u.text for u in mender.fill(new, [line])[0]] == [
        "thank you and I will hand it over to Sarah"]


class Recorder:
    def __init__(self) -> None:
        self.sounds: list[float] = []

    def align(self, sound: Any, utterances: list[Utterance], _language: str,
              _speech: Any = None) -> list[Word]:
        self.sounds.append(len(sound) / 100)
        return [w for u in utterances for w in align.proportional(u)]


@pytest.mark.parametrize(("second", "searches"), [(234.5, 2), (133.0, 1)])
def test_lines_far_apart_are_aligned_each_on_its_own(
        monkeypatch: pytest.MonkeyPatch, second: float, searches: int) -> None:
    recorder = Recorder()
    monkeypatch.setattr(align, "shared_aligner", lambda: recorder)
    lines = [Utterance(130.1, 130.8, "S2", "For Jim."),
             Utterance(second, second + 3.2, "S1", "would speak English is so insulting")]
    words = Timer(np.zeros(300 * 100), 100, "English", []).part(lines)
    assert len(recorder.sounds) == searches
    assert [w.text for w in words][:2] == ["For", "Jim."] and words[1].end < 131.0
