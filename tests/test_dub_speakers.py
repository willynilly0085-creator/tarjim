"""One person keeps one voice: the label of the voting pass that found a line ("p2.S1") is not
another speaker, and the main speaker of every piece of a long video speaks with the main voice."""
from tarjim.dub.lines import Line
from tarjim.dub.studio import cast
from tarjim.dub.voices import one_voice_each
from tarjim.models import Word
from tarjim.segment import build_cues


def talk(speaker: str, count: int, start: float) -> list[Word]:
    return [Word(f"w{k}", start + k * 0.4, start + k * 0.4 + 0.3, speaker) for k in range(count)]


def test_each_piece_main_speaker_speaks_with_the_same_voice() -> None:
    words = (talk("c0.S1", 20, 0.0) + talk("c0.S2", 3, 10.0) + talk("c0.p2.S1", 2, 12.0)
             + talk("c1.S2", 20, 300.0) + talk("c1.p2.S1", 3, 310.0))
    lines = [Line(0.0, 1.0, "c0.S1", "a"), Line(300.0, 301.0, "c1.S2", "b"),
             Line(310.0, 311.0, "c1.p2.S1", "c"), Line(12.0, 13.0, "c0.p2.S1", "d")]
    words, lines = one_voice_each(words, lines)
    assert [line.speaker for line in lines] == ["voice1", "voice1", "voice2", "voice1"]
    assert {w.speaker for w in words} == {"voice1", "voice2"}
    voices = cast(sorted({w.speaker for w in words}), "en")
    assert voices["voice1"] != voices["voice2"]


def test_a_line_found_by_another_pass_is_not_a_change_of_speaker() -> None:
    said = [Word("I", 0.0, 0.3, "S1"), Word("went", 0.3, 0.8, "S1"), Word("home", 0.8, 1.5, "S1"),
            Word("and", 1.6, 2.0, "p2.S1"), Word("slept", 2.0, 2.4, "p2.S1")]
    cues = build_cues(said, cuts=[])
    assert len(cues) == 1 and not cues[0].is_dialogue
