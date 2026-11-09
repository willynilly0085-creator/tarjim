"""Which stretches the tolerant aligner reads again (asr/weak.py, 2026-11-09): a run under the
clip's floor, a copy of words close by even when its letters are found (it finds them in the
words it copies), never a run said over another speaker only for scoring low."""
from tarjim.asr.weak import AROUND, Score, Weak, Window, joined, line_runs
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

HOST = Utterance(0.0, 2.0, "S1", "the whales sing")
GUEST = Utterance(1.5, 2.5, "S2", "really")


def placed(*lines: Utterance) -> list[Word]:
    found = []
    for u in lines:
        texts = u.text.split()
        step = (u.end - u.start) / len(texts)
        found += [Word(t, u.start + k * step, u.start + (k + 1) * step, u.speaker,
                       source="aligned") for k, t in enumerate(texts)]
    return found


def scored(low: set[str]) -> Score:
    return lambda run: 0.05 if run[0].text in low else 0.9


def test_a_run_is_a_line_s_words_so_a_copy_right_after_it_is_its_own() -> None:
    lines = [HOST, Utterance(2.05, 4.0, "S1", "the whales sing")]
    assert line_runs(placed(*lines), [0, 0, 0, 1, 1, 1]) == [(0, 3), (3, 6)]


def test_a_low_run_is_read_again_unless_said_over_another_speaker() -> None:
    lines = [Utterance(10.0, 11.0, "S1", "one two"), Utterance(20.0, 21.0, "S1", "three")]
    found = Weak(placed(*lines), lines, 0.3).windows(scored({"three"}))
    assert found == [Window(20.0 - AROUND, 21.0 + AROUND, False)]
    over = [HOST, GUEST]
    assert Weak(placed(*over), over, 0.3).windows(scored({"really"})) == []


def test_a_copy_is_read_again_even_when_found_and_only_copies_may_go() -> None:
    lines = [HOST, Utterance(2.2, 4.0, "S1", "the whales sing")]
    found = Weak(placed(*lines), lines, 0.3).windows(scored(set()))
    assert found == [Window(0.0 - AROUND, 4.0 + AROUND, True)]


def test_windows_that_meet_are_one_and_keep_to_copies_if_either_does() -> None:
    found = [Window(0.0, 4.0, False)]
    joined(found, Window(3.0, 6.0, True))
    joined(found, Window(9.0, 10.0, False))
    assert found == [Window(0.0, 6.0, True), Window(9.0, 10.0, False)]
