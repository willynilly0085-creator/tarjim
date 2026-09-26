from tarjim.dub.lines import lines_from
from tarjim.dub.voices import reference_spans
from tarjim.models import Cue, Word


def dialogue() -> Cue:
    ask = [Word("Once", 44.2, 44.6, "S5"), Word("a", 44.6, 44.7, "S5"),
           Word("month", 44.7, 45.1, "S5")]
    reply = [Word("Once?", 46.8, 47.3, "S1")]
    return Cue(44.2, 47.8, ask + reply, text="- مرة بالشهر || - مرة بالشهر؟", parts=[ask, reply])


def test_dialogue_becomes_two_lines_each_with_its_own_speaker_and_start() -> None:
    lines = lines_from([dialogue()], total=60.0)
    assert [(line.speaker, line.start, line.text) for line in lines] == [
        ("S5", 44.2, "مرة بالشهر"), ("S1", 46.8, "مرة بالشهر؟")]
    assert lines[0].until == 46.8


def test_empty_translations_are_not_spoken() -> None:
    silent = Cue(1.0, 2.0, [Word("um", 1.0, 2.0, "S1")], text="")
    assert lines_from([silent], total=10.0) == []


def test_each_speaker_gets_their_own_longest_clean_stretches() -> None:
    words = [Word("a", 0.0, 4.0, "S1"), Word("b", 4.0, 9.0, "S1"), Word("c", 9.5, 10.0, "S2"),
             Word("d", 11.0, 13.0, "S2"), Word("e", 14.0, 20.0, "S1")]
    spans = reference_spans(words)
    assert spans["S1"] == [(0.0, 9.0), (14.0, 17.0)]
    assert spans["S2"] == [(11.0, 13.0)]


def test_engine_falls_back_when_a_language_or_key_is_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import pytest

    from tarjim.dub import make

    monkeypatch.setattr(make, "setting", lambda _name: "")
    assert make.choose("fish", "ar") == "clone"
    assert make.choose("studio", "nl") == "clone"
    assert make.choose("clone", "ur") == "studio"
    with pytest.raises(make.DubUnavailable):
        make.choose("clone", "sw")


def test_vowels_are_added_without_changing_letters_digits_or_latin() -> None:
    from tarjim.dub.tashkeel import add_vowels

    class Model:
        def do_tashkeel_batch(self, batch: list[str], verbose: bool) -> list[str]:
            return ["مَرَّة بِالشَّهْر"]

    assert add_vowels(["مرة بالشهر 3 OK"], Model()) == ["مَرَّة بِالشَّهْر 3 OK"]


def test_each_line_starts_where_its_speaker_starts() -> None:
    import numpy as np

    from tarjim.dub.audio import RATE
    from tarjim.dub.lines import Line
    from tarjim.dub.mix import mix

    background = np.zeros((RATE * 4, 2), dtype=np.float32)
    voice = np.full(RATE // 2, 0.5, dtype=np.float32)
    track = mix([Line(1.0, 3.0, "S1", "hi")], [voice], background)
    assert track[RATE - 1, 0] == 0.0
    assert track[RATE, 0] == 0.5 and track[RATE, 1] == 0.5


def test_numbers_are_spelled_out_for_the_voice_but_not_for_the_subtitle() -> None:
    from tarjim.dub.make import spell_numbers

    assert spell_numbers("18 مرة في الشهر", "ar") == "ثمانية عشر مرة في الشهر"
    assert spell_numbers("every 3 months", "en") == "every three months"
    assert spell_numbers("كل 3 شهور", "xx") == "كل 3 شهور"
