"""Words of a line retimed onto the local listener's words that it did not hear share the time
between the words around them by their length, as the aligner's own gaps do (asr/align.fill_gaps).
Before 2026-11-08 the second and later of them all sat on one instant, zero long."""
from itertools import pairwise

from tarjim.asr.align import longest
from tarjim.asr.fuse import fill, fuse
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word


def test_a_run_of_unheard_words_shares_the_gap_by_length() -> None:
    texts = ["three", "two", "personally,", "zero"]
    spans = fill(texts, [(1.0, 1.2), None, None, (3.0, 3.2)], (0.0, 9.0))
    middle = spans[1:3]
    assert middle[0][0] == 1.2 and middle[-1][1] == 3.0
    assert all(end > start for start, end in middle)
    assert all(a[1] == b[0] for a, b in pairwise(spans[:3]))
    ratio = (middle[1][1] - middle[1][0]) / (middle[0][1] - middle[0][0])
    assert abs(ratio - longest("personally,") / longest("two")) < 1e-9


def test_unheard_words_at_either_end_are_not_zero_long() -> None:
    spans = fill(["a", "b", "c", "d"], [None, (2.0, 2.3), (2.4, 2.6), None], (0.0, 9.0))
    assert spans[0][1] == 2.0 and spans[0][1] > spans[0][0]
    assert spans[-1][0] == 2.6 and spans[-1][1] > spans[-1][0]


def test_a_retimed_line_has_no_word_on_one_instant() -> None:
    line = Utterance(10.0, 13.0, "S1", "one two three four five")
    aligned = [Word(w, 20.0 + k, 20.5 + k, "S1") for k, w in enumerate(line.text.split())]
    heard = [Word("one", 10.1, 10.4), Word("two", 10.5, 10.8), Word("five", 12.4, 12.7)]
    fused = fuse(aligned, [line], heard)
    assert [w.text for w in fused] == line.text.split()
    assert all(w.end > w.start for w in fused)
    assert all(a.end <= b.start + 1e-9 for a, b in pairwise(fused))
