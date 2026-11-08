"""The tolerant reading of the aligner's letters (asr/tolerant.py, 2026-11-08): with the text
exactly as said it reads like the strict one; sound the text does not hold is taken by the star
instead of pulling the words beside it; a word that is not said is stepped over."""
import numpy as np

from tarjim.asr.costs import Costs
from tarjim.asr.ctc import FRAME, token_spans
from tarjim.asr.tolerant import Text, decoded, tolerant_spans

LETTERS = "abcdefghijklmnopqrstuvwxyz"
CLASSES = 4 + len(LETTERS)
FLOOR = -12.0
STAR = Costs(star_delta=1.0)
SKIP = Costs(star_delta=1.0, skip=True)


def ids(word: str) -> list[int]:
    return [4 + LETTERS.index(ch) for ch in word]


def sound(frames: int, said: dict[int, str]) -> np.ndarray:
    """Blank everywhere but where a word is said: each letter two frames, a blank between."""
    logp = np.full((frames, CLASSES), FLOOR)
    logp[:, 0] = 0.0
    for at, word in said.items():
        for k, letter in enumerate(ids(word)):
            first = at + 3 * k
            logp[first:first + 2] = FLOOR
            logp[first:first + 2, letter] = 0.0
    return logp


def text(*words: str) -> Text:
    tokens = [t for word in words for t in ids(word)]
    owners = [w for w, word in enumerate(words) for _ in word]
    return Text(tokens, owners)


def starts(spans: list[tuple[float, float, float] | None]) -> list[int]:
    return [round(span[0] / FRAME) for span in spans if span is not None]


def chant(logp: np.ndarray, low: int, high: int) -> np.ndarray:
    """Letters the text does not hold said without a pause, the words' own letters close."""
    logp = logp.copy()
    logp[low:high] = FLOOR
    logp[low:high, 0] = -10.0
    logp[low:high, ids("t") + ids("d")] = -5.0
    for t in range(low, high):
        logp[t, ids("xqzj")[t % 4]] = 0.0
    return logp


def test_exact_text_reads_like_the_strict_aligner() -> None:
    logp = sound(200, {10: "cat", 60: "dog", 120: "bird"})
    strict = token_spans(logp, ids("catdogbird"))
    for costs in (None, STAR, SKIP):
        placed = tolerant_spans(logp, text("cat", "dog", "bird"), costs)
        assert placed.spans == strict
        assert placed.placed == [True, True, True]
        assert placed.absorbed == []


def test_untranscribed_stretch_is_taken_by_the_star() -> None:
    logp = chant(sound(200, {10: "cat", 130: "dog"}), 20, 120)  # 2 s nobody wrote down
    strict = token_spans(logp, ids("catdog"))
    placed = tolerant_spans(logp, text("cat", "dog"), STAR)
    truth = [10, 13, 16, 130, 133, 136]
    assert all(abs(a - b) <= 1 for a, b in zip(starts(placed.spans), truth, strict=True))
    assert placed.absorbed and placed.absorbed[0][1] - placed.absorbed[0][0] >= 1.9
    assert strict is not None
    # the documented contrast: the strict path stretches a neighbour's letter over the chant
    ends = [round(span[1] / FRAME) for span in strict]
    assert ends[2] > 30 or starts(strict)[3] < 120


def test_invented_word_is_stepped_over() -> None:
    logp = sound(100, {10: "cat", 60: "dog"})
    placed = tolerant_spans(logp, text("cat", "fox", "dog"), SKIP)
    assert placed.placed == [True, False, True]
    assert placed.spans[3:6] == [None, None, None]
    assert starts(placed.spans) == [10, 13, 16, 60, 63, 66]
    squeezed = tolerant_spans(logp, text("cat", "fox", "dog"), STAR)
    assert squeezed.placed == [True, True, True]


def test_moves_are_one_byte_per_frame_and_state() -> None:
    logp = sound(100, {10: "cat", 60: "dog"})
    words = text("cat", "dog")
    found = decoded(logp, words, SKIP)
    states = 2 * len(words.tokens) + 1 + 3  # the strict states and a star at each boundary
    assert found.back.dtype == np.int8
    assert found.back.shape == (100, states)
    assert decoded(logp, words, None).back.shape == (100, 2 * len(words.tokens) + 1)


def test_long_invented_word_is_stepped_over() -> None:
    long = (LETTERS * 3)[:70]
    logp = sound(120, {10: "cat", 80: "dog"})
    placed = tolerant_spans(logp, text("cat", long, "dog"), SKIP)
    assert placed.placed == [True, False, True]
    assert starts(placed.spans) == [10, 13, 16, 80, 83, 86]


def test_star_never_sits_on_hard_frames() -> None:
    logp = chant(sound(200, {10: "cat", 130: "dog"}), 20, 120)
    hard = np.zeros(200, dtype=bool)
    hard[50:80] = True
    found = decoded(logp, text("cat", "dog"), STAR, hard)
    assert found.on_star().any()
    assert not (found.on_star() & hard).any()


def test_word_windows_hold_as_in_the_strict_aligner() -> None:
    flat = np.log(np.full((100, CLASSES), 1 / CLASSES))
    bounds = (np.array([60, 60]), np.array([80, 80]))
    strict = token_spans(flat, ids("ab"), bounds)
    placed = tolerant_spans(flat, Text(ids("ab"), [0, 0], bounds), STAR)
    assert placed.spans == strict


def test_nothing_to_place_and_too_little_sound() -> None:
    assert tolerant_spans(sound(10, {}), Text([], []), STAR).spans == []
    short = tolerant_spans(sound(2, {}), text("cat"), STAR)
    assert short.spans == [None, None, None] and short.placed == [False]
