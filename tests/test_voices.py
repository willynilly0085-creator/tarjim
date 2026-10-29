"""Each speaker's lines keep a colour of their own; the main speaker stays off-white."""
from tarjim.models import Cue, Word
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.voices import BACK_TO_MAIN, MAIN, OTHERS, voices

YELLOW = OTHERS[0]


def said(text: str, start: float, speaker: str) -> Cue:
    words = [Word(w, start + k * 0.3, start + k * 0.3 + 0.2, speaker)
             for k, w in enumerate(text.split())]
    return Cue(words[0].start, words[-1].end + 1.0, words, text=text, parts=[list(words)])


def test_the_main_speaker_keeps_the_usual_colour_and_the_other_turns_yellow() -> None:
    host = said("I guarantee you it is not true at all", 0.0, "S1")
    guest = said("Right", 5.0, "S2")
    assert voices([host, guest]) == {"S2": YELLOW}
    ass = render_ass([host, guest], Canvas(1920, 1080))
    lines = [e for e in ass.splitlines() if e.startswith("Dialogue:")]
    assert YELLOW not in lines[0] and YELLOW in lines[1]
    assert f"Style: Default,Dubai,63,{MAIN},{MAIN}," in ass


def test_one_speaker_gets_no_colour_tags() -> None:
    ass = render_ass([said("Hello there", 0.0, "S1")], Canvas(1920, 1080))
    assert "\\c&H" not in ass


def test_each_line_of_a_dialogue_takes_its_own_speaker_colour() -> None:
    ask = [Word("Same", 0.0, 0.5, "S2"), Word("here", 0.5, 0.9, "S2")]
    reply = [Word("Exactly", 0.95, 1.2, "S1")]
    main = said("one two three four five six", 3.0, "S1")
    cue = Cue(0.0, 2.0, ask + reply, text="نفس الشيء || بالضبط", parts=[ask, reply])
    event = next(e for e in render_ass([cue, main], Canvas(1920, 1080)).splitlines()
                 if "نفس" in e)
    top, bottom = event.split("\\N")
    assert YELLOW in top and YELLOW not in bottom and BACK_TO_MAIN in bottom


def test_speakers_are_ranked_within_each_piece_of_a_long_video() -> None:
    cues = [said("a b c d e f", 0.0, "c0.S1"), said("yes", 3.0, "c0.S2"),
            said("g h i j k l", 400.0, "c1.S2"), said("ok", 403.0, "c1.p2.S1")]
    assert voices(cues) == {"c0.S2": YELLOW, "c1.S1": YELLOW}


def test_the_outline_is_softened_only_without_a_box() -> None:
    cue = said("Hello there", 0.0, "S1")
    assert "\\blur" in render_ass([cue], Canvas(1920, 1080))
    assert "\\blur" not in render_ass([cue], Canvas(1920, 1080, bright=True))
