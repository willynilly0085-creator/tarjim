"""How tolerant the aligner may be on one clip (asr/costs.py, 2026-11-08): measured on the runs
the strict check finds, kept at a floor, and off when too few runs are found."""
import numpy as np

from tarjim.asr.costs import FLOOR, MIN_RUNS, Run, calibrated, measured
from tarjim.asr.ctc import token_spans
from tarjim.asr.tolerant import Text, tolerant_spans

LETTERS = "abcdefghijklmnopqrstuvwxyz"
CLASSES = 4 + len(LETTERS)
WORD = "lighthouse"  # ten letters, three frames each: 30 letter frames a run


def ids(word: str) -> list[int]:
    return [4 + LETTERS.index(ch) for ch in word]


def clip(runs: int, rival: bool = False) -> tuple[np.ndarray, list[Run]]:
    """`runs` times WORD, each letter three frames with a blank after. With `rival`, a letter
    is one weak frame where the blank stays loudest and another letter sits 0.75 above it, as
    on a soft syllable: the text explains every letter heard, yet the said one is not the
    loudest letter there."""
    logp = np.full((runs * 50, CLASSES), -12.0)
    logp[:, 0] = 0.0
    found = []
    for r in range(runs):
        for k, letter in enumerate(ids(WORD)):
            first = r * 50 + 5 + 4 * k
            if rival:
                logp[first, letter], logp[first, ids("z")] = -1.0, -0.25
            else:
                logp[first:first + 3, 0], logp[first:first + 3, letter] = -12.0, 0.0
        found.append(Run(ids(WORD), r * 50, r * 50 + 50))
    return logp, found


def test_peaky_letters_keep_the_floor() -> None:
    logp, runs = clip(MIN_RUNS)
    gaps = measured(logp, runs)
    assert gaps.runs == MIN_RUNS and gaps.frames == MIN_RUNS * 30
    assert gaps.spread["p80"] == 0.0
    costs = calibrated(logp, runs)
    assert costs is not None and costs.star_delta == FLOOR
    assert not costs.skip


def test_the_spread_of_letters_sets_the_star() -> None:
    logp, runs = clip(20, rival=True)  # still found: e^-1 is above agree.FOUND
    gaps = measured(logp, runs)
    assert gaps.frames == 200 and gaps.unexplained == 0.0 and gaps.spread["p80"] == 0.75
    costs = calibrated(logp, runs, skip=True)
    assert costs is not None and costs.star_delta == 1.75 and costs.skip


def test_too_few_runs_found_leaves_the_aligner_strict() -> None:
    logp, runs = clip(MIN_RUNS - 1)
    assert calibrated(logp, runs, skip=True) is None
    words = Text(ids(WORD) * 2, [0] * 10 + [1] * 10)
    assert tolerant_spans(logp, words, None).spans == token_spans(logp, ids(WORD) * 2)


def test_runs_the_strict_check_does_not_find_are_not_counted() -> None:
    logp, runs = clip(MIN_RUNS)
    elsewhere = [Run(ids("jqxv"), r.low, r.high) for r in runs]
    gaps = measured(logp, elsewhere)
    assert gaps.runs == 0 and gaps.frames == 0
    assert calibrated(logp, elsewhere) is None


def test_letters_the_text_does_not_explain_leave_it_strict() -> None:
    """Every second letter lost in reading the script: the runs are still found, but half the
    letters heard in them are not the text's, so nothing tells a word not said."""
    logp, runs = clip(MIN_RUNS + 2)
    spoilt = [Run(r.tokens[::2], r.low, r.high) for r in runs]
    gaps = measured(logp, spoilt)
    assert gaps.runs == MIN_RUNS + 2 and gaps.frames >= 200
    assert gaps.unexplained > 0.3
    assert measured(logp, runs).unexplained == 0.0
    assert calibrated(logp, spoilt, skip=True) is None


def test_short_runs_with_too_few_letter_frames_leave_it_strict() -> None:
    logp = np.full((MIN_RUNS * 10, CLASSES), -12.0)
    logp[:, 0] = 0.0
    runs = []
    for r in range(MIN_RUNS):
        logp[r * 10 + 2, 0], logp[r * 10 + 2, ids("a")] = -12.0, 0.0
        runs.append(Run(ids("a"), r * 10, r * 10 + 10))
    assert measured(logp, runs).runs == MIN_RUNS
    assert calibrated(logp, runs) is None
