from tarjim.asr.align import proportional
from tarjim.listen.gemini_listen import Utterance, parse


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
