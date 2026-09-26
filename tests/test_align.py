import numpy as np

from tarjim.asr.align import Slot, densest, fill_gaps, longest, proportional
from tarjim.listen.gemini_listen import Utterance, parse


def test_word_without_letters_sits_between_its_neighbours() -> None:
    slots = [Slot("I'm", "S1", 0, 1.0, 1.2, True), Slot("18", "S1", 0),
             Slot("now", "S1", 0, 1.8, 2.0, True)]
    fill_gaps(slots)
    assert (slots[1].start, slots[1].end) == (1.2, 1.8)


def test_word_scattered_across_a_pause_keeps_the_side_with_most_letters() -> None:
    speech = np.ones(300, dtype=bool)
    speech[100:200] = False
    spans = [(1.0, 1.1, 0.1), (1.1, 1.2, 0.1), (1.3, 1.4, 0.1), (4.1, 4.2, 0.1)]
    assert densest(spans, speech) == (1.0, 1.4)


def test_short_word_cannot_be_stretched_over_a_second() -> None:
    assert longest("And") < 1.0
    assert longest("personally,") > longest("And")


def test_proportional_fallback_spans_the_utterance_in_order() -> None:
    words = proportional(Utterance(10.0, 12.0, "S1", "Once a month?"))
    assert [w.text for w in words] == ["Once", "a", "month?"]
    assert words[0].start == 10.0
    assert abs(words[-1].end - 12.0) < 1e-9
    assert all(w.speaker == "S1" for w in words)


def test_parse_rejects_broken_rows() -> None:
    assert parse({"start": 1, "end": 0.5, "speaker": "S1", "text": "hi"}) is None
    assert parse({"start": "x", "end": 2, "text": "hi"}) is None
    assert parse({"start": 1, "end": 2, "speaker": "S2", "text": " Yeah. "}) == \
        Utterance(1.0, 2.0, "S2", "Yeah.")
