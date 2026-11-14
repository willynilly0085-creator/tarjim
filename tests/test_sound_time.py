"""A line the listener put where it is not said goes where the sound holds its letters, on any
computer: until 2026-11-14 only the local listener's words corrected a line's time, and passes
that wrote the same lines on a faster clock pressed them seconds before their speech."""
from dataclasses import replace

import numpy as np
import pytest

from tarjim.asr.ctc import FRAME
from tarjim.listen import soundtime
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.soundtime import Ears, on_the_sound
from tests.test_emissions_once import HOP, VOCAB, Hearing

SECONDS = 70.0
SAID = {5.0: "alphabravo", 30.0: "charliedelta", 55.0: "echofoxtrot", 56.0: "yes"}
WHOLE = (0.0, SECONDS)


def ears() -> Ears:
    """Each letter is heard for three frames from the time its word is said."""
    labels = np.zeros(int(SECONDS / FRAME), dtype=np.float32)
    for at, word in SAID.items():
        for k, ch in enumerate(word):
            first = int(at / FRAME) + 3 * k
            labels[first:first + 3] = VOCAB[ch]
    return Ears(Hearing()(np.repeat(labels, HOP)), lambda text: [VOCAB[ch] for ch in text],
                "English")


def line(start: float, text: str, request: str = "k0.v") -> Utterance:
    return Utterance(start, start + 2.0, "S1", text, piece=WHOLE, request=request)


def starts(lines: list[Utterance]) -> list[float]:
    """To the half second: a line moved starts with its first letter heard, a frame or so off."""
    return [round(u.start * 2) / 2 for u in lines]


def test_lines_written_on_a_faster_clock_go_where_they_are_said() -> None:
    fast = [line(4.5, "alphabravo"), line(20.0, "charliedelta"), line(36.0, "echofoxtrot")]
    placed = on_the_sound(fast, ears())
    assert starts(placed) == [4.5, 30.0, 55.0]  # the first is within the aligner's reach
    assert abs(placed[1].end - 30.72) < 0.1 and placed[1].text == "charliedelta"


def test_lines_heard_where_they_stand_are_left_exactly_as_they_were() -> None:
    right = [line(4.5, "alphabravo"), line(29.5, "charliedelta"), line(54.6, "echofoxtrot")]
    placed = on_the_sound(right, ears())
    assert [(u.start, u.end) for u in placed] == [(u.start, u.end) for u in right]


def test_a_short_reply_goes_with_the_line_before_it() -> None:
    fast = [line(4.5, "alphabravo"), line(36.0, "echofoxtrot"), line(38.5, "yes")]
    assert starts(on_the_sound(fast, ears())) == [4.5, 55.0, 56.0]
    stays = [line(4.5, "alphabravo"), line(20.0, "yes")]
    assert starts(on_the_sound(stays, ears())) == [4.5, 20.0]


def test_a_line_the_sound_does_not_hold_stays_where_it_was_put() -> None:
    lines = [line(4.5, "alphabravo"), line(20.0, "neversaidatall"), line(54.5, "echofoxtrot")]
    assert starts(on_the_sound(lines, ears())) == [4.5, 20.0, 54.5]


def test_lines_asked_about_again_and_local_words_are_not_searched() -> None:
    again = replace(line(20.0, "charliedelta", request=""), piece=(18.0, 24.0))
    local = line(36.0, "echofoxtrot", request="local")
    assert starts(on_the_sound([line(4.5, "alphabravo"), again, local], ears())) == [
        4.5, 20.0, 36.0]


def test_a_stretch_too_long_to_search_at_once_keeps_its_times(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(soundtime, "CELLS", 1000)
    fast = [line(4.5, "alphabravo"), line(20.0, "charliedelta")]
    assert starts(on_the_sound(fast, ears())) == [4.5, 20.0]
    assert "too long to search" in capsys.readouterr().out


def test_a_pause_inside_a_line_leaves_its_last_words_its_own() -> None:
    """Said in two halves three seconds apart: the line covers both."""
    paused = Utterance(20.0, 22.0, "S1", "charliedelta echofoxtrot", piece=WHOLE, request="k0.v")
    said = dict(SAID)
    try:
        SAID.clear()
        SAID.update({40.0: "charliedelta", 44.0: "echofoxtrot"})
        [placed] = on_the_sound([paused], ears())
    finally:
        SAID.clear()
        SAID.update(said)
    assert abs(placed.start - 40.0) < 0.1 and abs(placed.end - 44.66) < 0.1
