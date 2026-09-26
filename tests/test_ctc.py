import numpy as np

from tarjim.asr.ctc import FRAME, token_spans

BLANK, A, B = 0, 1, 2


def emissions(frames: list[int], classes: int = 3) -> np.ndarray:
    logp = np.full((len(frames), classes), np.log(0.01))
    for t, label in enumerate(frames):
        logp[t, label] = np.log(0.98)
    return logp


def test_word_after_long_silence_starts_where_it_is_spoken() -> None:
    frames = [A, A] + [BLANK] * 150 + [B, B, B] + [BLANK] * 5
    spans = token_spans(emissions(frames), [A, B])
    assert spans is not None
    (a_start, a_end, _), (b_start, b_end, _) = spans
    assert a_start == 0 and a_end == 2 * FRAME
    assert abs(b_start - 152 * FRAME) < 1e-9
    assert abs(b_end - 155 * FRAME) < 1e-9


def test_repeated_token_needs_a_blank_between() -> None:
    frames = [A, BLANK, A, BLANK]
    spans = token_spans(emissions(frames), [A, A])
    assert spans is not None
    assert spans[0][1] <= spans[1][0]


def test_confident_frames_score_higher_than_noise() -> None:
    clear = token_spans(emissions([A, A, B, B]), [A, B])
    noisy = token_spans(np.log(np.full((4, 3), 1 / 3)), [A, B])
    assert clear is not None and noisy is not None
    assert clear[0][2] > noisy[0][2]


def test_weak_evidence_stays_inside_its_sentence_window() -> None:
    flat = np.log(np.full((100, 3), 1 / 3))
    bounds = (np.array([60, 60]), np.array([80, 80]))
    spans = token_spans(flat, [A, B], bounds)
    assert spans is not None
    assert all(start >= 60 * FRAME and end <= 80 * FRAME for start, end, _ in spans)


def test_too_few_frames_returns_none() -> None:
    assert token_spans(emissions([A]), [A, B, A]) is None
