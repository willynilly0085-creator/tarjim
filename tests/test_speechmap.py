"""One speech map per clip, from the letters the aligner hears once and one voice detector run,
with three tiers (2026-11-09): hard silence, where letters pay the full penalty; soft, where only
a heard line calls it speech or a little letter mass is heard, which costs a little; and speech,
where the detector or the letters hear it (a chant the detector takes for silence)."""
import json

import numpy as np
import pytest

from tarjim.asr import speechmap
from tarjim.asr.ctc import BLANK, FRAME
from tarjim.asr.speechmap import HARD, SOFT, SPEECH, SpeechMap, build, restored
from tarjim.asr.vad import SILENCE_PENALTY, mute

LETTERS = 5
SECONDS = 60.0
FRAMES = int(SECONDS / FRAME)


def at(second: float) -> int:
    return int(second / FRAME)


def letters(said: list[tuple[float, float]], faint: list[tuple[float, float]] = ()) -> np.ndarray:
    """Blank-confident frames, with a letter every second frame where something is `said`, and a
    weak one every second frame where it is `faint` (letter mass between tau/2 and tau)."""
    probs = np.full((FRAMES, LETTERS), 0.001)
    probs[:, BLANK] = 1.0
    for start, end in said:
        probs[at(start):at(end):2, BLANK] = 0.01
        probs[at(start):at(end):2, 1] = 0.99
    for start, end in faint:
        probs[at(start):at(end):2, BLANK] = 0.7
        probs[at(start):at(end):2, 2] = 0.3
    return np.log(probs / probs.sum(axis=1, keepdims=True))


TALK = [(0.0, 20.0), (40.0, 50.0)]  # the voice detector heard these
CHANT = (25.0, 32.0)  # the detector took it for silence; the letters are there


def chanted() -> SpeechMap:
    return build(letters([*TALK, CHANT]), FRAMES, TALK)


def test_blank_confident_silence_is_hard() -> None:
    made = chanted()
    assert made.source == "vad+ctc"
    assert (made.tier[at(34.0):at(39.0)] == HARD).all()
    assert (made.tier[at(52.0):] == HARD).all()


def test_letters_the_detector_missed_are_speech_and_listed_as_chant() -> None:
    made = chanted()
    assert (made.tier[at(25.5):at(31.5)] == SPEECH).all()
    (start, end), = made.ctc_only()
    assert start == pytest.approx(25.0, abs=0.2) and end == pytest.approx(32.0, abs=0.2)
    assert any(a <= 26.0 and b >= 31.0 for a, b in made.speech())  # coverage sees the chant


def test_a_heard_line_over_silence_is_soft_never_speech() -> None:
    heard = chanted().heard([(33.0, 39.0)])
    assert (heard.tier[at(33.5):at(38.5)] == SOFT).all()
    assert not (heard.tier[at(33.0):at(39.0)] == SPEECH).any()
    assert (heard.tier[at(25.5):at(31.5)] == SPEECH).all()  # speech stays speech


def test_a_heard_line_is_padded_as_the_detector_speech_is() -> None:
    """2026-11-09: before the map a heard line was speech with the detector's padding either
    side (asr/vad.PAD); without it, 0.04 s of a line's onset fell back to hard silence and an
    overlapped line's last words were squeezed 0.3 s early on the bench (en_long_three_pieces,
    slip). A line is soft over the same padding."""
    from tarjim.asr.vad import PAD

    heard = chanted().heard([(33.0, 39.0)])
    assert (heard.tier[at(33.0 - PAD):at(39.0 + PAD)] == SOFT).all()
    assert (heard.tier[at(32.5):at(33.0 - PAD) - 1] == HARD).all()  # and no further


def test_faint_letter_mass_without_a_run_is_soft_and_a_quiet_bed_stays_hard() -> None:
    """A music bed the letters hardly hear keeps the full penalty, as before (no energy term:
    a loud bed would otherwise lose its protection, 2026-11-09 review)."""
    made = build(letters(TALK, faint=[(33.0, 38.0)]), FRAMES, TALK)
    assert (made.tier[at(33.5):at(37.5)] == SOFT).all()
    assert (made.tier[at(52.0):] == HARD).all()


def test_without_a_detector_the_threshold_comes_from_the_letters() -> None:
    made = build(letters([*TALK, CHANT]), FRAMES, [])
    assert made.source == "ctc"
    assert speechmap.TAU_LOW <= made.tau <= speechmap.TAU_HIGH
    assert (made.tier[at(1.0):at(19.0)] == SPEECH).all()
    assert (made.tier[at(34.0):at(39.0)] == HARD).all()


def test_nothing_to_measure_by_uses_the_default() -> None:
    quiet = build(letters([]), FRAMES, [])
    assert quiet.source == "ctc-uncalibrated" and quiet.tau == speechmap.TAU_DEFAULT
    assert (quiet.tier == HARD).all()
    deaf = build(None, FRAMES, TALK)  # a stand-in aligner hears no letters
    assert deaf.source == "none"
    assert (deaf.tier[at(1.0):at(19.0)] == SPEECH).all() and deaf.tier[at(30.0)] == HARD


def test_the_penalties_fall_on_letters_alone() -> None:
    made = chanted().heard([(33.0, 39.0)])
    logp = letters(TALK)
    muted = mute(logp, made.penalty())
    assert np.array_equal(muted[:, BLANK], logp[:, BLANK])
    assert muted[at(36.0), 1] == pytest.approx(logp[at(36.0), 1] - speechmap.SOFT_PENALTY)
    assert muted[at(55.0), 1] == pytest.approx(logp[at(55.0), 1] - SILENCE_PENALTY)
    assert muted[at(10.0), 1] == logp[at(10.0), 1]


def test_the_map_round_trips_through_its_summary() -> None:
    made = chanted()
    again = restored(json.loads(json.dumps(made.summary())))
    assert np.array_equal(again.tier, made.tier) and np.array_equal(again.vad, made.vad)
    assert (again.tau, again.source, again.regions) == (made.tau, made.source, made.regions)


def test_a_stretch_reads_the_clip_map_sliced() -> None:
    made = chanted()
    view = made.view(at(20.0), at(35.0))
    assert np.array_equal(view.tier, made.tier[at(20.0):at(35.0)])
    assert np.array_equal(view.vad, made.vad[at(20.0):at(35.0)])
    past = made.view(at(55.0), FRAMES + 50)  # a stretch reaching past the clip's last frame
    assert past.frames == FRAMES + 50 - at(55.0)
