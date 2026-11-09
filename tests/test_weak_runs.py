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
    assert found == [Window(20.0 - AROUND, 21.0 + AROUND, None)]
    over = [HOST, GUEST]
    assert Weak(placed(*over), over, 0.3).windows(scored({"really"})) == []


def test_a_copy_is_read_again_even_when_found_and_only_copies_may_go() -> None:
    lines = [HOST, Utterance(2.2, 4.0, "S1", "the whales sing")]
    found = Weak(placed(*lines), lines, 0.3).windows(scored(set()))
    assert found == [Window(0.0 - AROUND, 4.0 + AROUND, "S1")]


def test_windows_of_one_kind_that_meet_are_one() -> None:
    found = [Window(0.0, 4.0, None)]
    joined(found, Window(3.0, 6.0, None))
    joined(found, Window(5.0, 7.0, "S1"))
    joined(found, Window(6.5, 8.0, "S1"))
    assert found == [Window(0.0, 6.0, None), Window(5.0, 8.0, "S1")]


def test_a_copy_is_of_its_own_speaker_and_its_window_reads_that_speaker_alone() -> None:
    """The review of 2026-11-09: S2's line said again by S1 is no copy; S1's line written
    twice is, and only S1's words are read again in its window."""
    lines = [Utterance(0.0, 1.0, "S2", "water at every station", request="k0.v"),
             Utterance(1.5, 2.5, "S1", "water at every station", request="k0.v"),
             Utterance(3.0, 4.0, "S1", "water at every station", request="k0.v")]
    found = Weak(placed(*lines), lines, 0.3).windows(scored(set()))
    assert found == [Window(1.5 - AROUND, 4.0 + AROUND, "S1")]


def test_windows_of_two_speakers_stay_apart() -> None:
    found = [Window(0.0, 4.0, "S1")]
    joined(found, Window(3.0, 6.0, "S2"))
    assert found == [Window(0.0, 4.0, "S1"), Window(3.0, 6.0, "S2")]
