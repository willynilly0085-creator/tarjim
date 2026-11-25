"""2026-11-25: the background of the owner's clip kept a trace of the English speech, 16 dB
over its quiet in the speech band, heard as whispering under the dub once it was raised."""
import numpy as np
import pytest

from tarjim.dub import duck, mix
from tarjim.dub.audio import RATE
from tarjim.dub.lines import Line
from tarjim.dub.separate import Stems

TALK = Line(2.0, 5.0, "voice1", "هلا", "Hi", 4.0)


def test_the_background_is_lower_only_while_someone_talks() -> None:
    gain = duck.envelope([TALK], 7 * RATE)
    assert gain[3 * RATE] == pytest.approx(duck.DUCK)
    assert gain[RATE] == pytest.approx(1.0) and gain[6 * RATE] == pytest.approx(1.0)


def test_it_slopes_in_rather_than_jumping() -> None:
    gain = duck.envelope([TALK], 7 * RATE)
    assert duck.DUCK < gain[2 * RATE - int(0.05 * RATE)] < 1.0


def test_a_background_that_could_not_be_separated_is_left_as_it_is() -> None:
    mixture = np.ones((7 * RATE, 2), dtype=np.float32)
    assert duck.under_voices(Stems(mixture[:, 0], mixture, False), [TALK]) is mixture
    ducked = duck.under_voices(Stems(mixture[:, 0], mixture, True), [TALK])
    assert ducked[3 * RATE, 0] == pytest.approx(duck.DUCK) and ducked[3 * RATE, 1] == ducked[
        3 * RATE, 0]


def test_lines_said_louder_or_softer_are_brought_toward_the_middle_one() -> None:
    soft, middle, loud = (np.full(RATE, level, dtype=np.float32) for level in (0.1, 0.2, 0.9))
    evened = mix.evened([soft, middle, loud, np.zeros(0, dtype=np.float32)])
    assert [round(float(w.max()), 3) for w in evened[:3]] == [0.2, 0.2, 0.45]
    assert evened[3].size == 0


def test_a_laugh_between_the_lines_is_heard_in_the_persons_own_voice() -> None:
    """2026-11-25: the laughs at the end of the owner's clip went with the original voices."""
    background = np.zeros((7 * RATE, 2), dtype=np.float32)
    laugh = np.zeros(7 * RATE, dtype=np.float32)
    laugh[int(5.5 * RATE):int(6.5 * RATE)] = 0.3
    laugh[3 * RATE] = 0.3  # the English under a dubbed line is not brought back
    under = duck.under_voices(Stems(laugh, background, True), [TALK])
    assert under[6 * RATE, 0] == pytest.approx(0.3) and under[3 * RATE, 0] == 0.0
