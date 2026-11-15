"""The summary to post writes about a speaker in the gender of their voice. On 2026-11-15 a
clip spoken by a woman was summarised "the speaker points out" in the masculine: her voice had
been measured and told to the model by her label, but the lines it was given carried no labels,
and it was told to follow the voices only where a speaker talks about themself."""
from tarjim import post
from tarjim.languages import language
from tarjim.models import Cue, Word

AR = language("ar")
VOICES = (("S1", "high"), ("S2", "low"))


def line(start: float, speaker: str, text: str) -> Cue:
    return Cue(start, start + 1.0, [Word("x", start, start + 1.0, speaker)], text)


def test_each_line_carries_its_speaker_when_the_voices_are_known() -> None:
    cues = [line(0.0, "S1", "الجميع يريد الاقتراب من السلطة"), line(2.0, "S2", "المسلسل")]
    assert post.spoken(cues, VOICES) == ["S1: الجميع يريد الاقتراب من السلطة", "S2: المسلسل"]


def test_an_exchange_carries_both_its_speakers() -> None:
    first, second = Word("a", 0.0, 0.5, "S1"), Word("b", 0.5, 1.0, "S2")
    cue = Cue(0.0, 1.0, [first, second], "نعم || لا", [[first], [second]])
    assert post.spoken([cue], VOICES) == ["S1+S2: نعم لا"]


def test_lines_carry_no_label_when_no_voice_was_measured_or_nobody_is_labelled() -> None:
    cues = [line(0.0, "S1", "مرحبا")]
    assert post.spoken(cues) == ["مرحبا"]
    assert post.spoken([line(0.0, "", "مرحبا")], (("", "high"),)) == ["مرحبا"]


def test_the_model_is_told_to_write_about_a_speaker_in_their_voice_s_gender() -> None:
    asked = post.prompt("a title", AR, ["S1: مرحبا"], VOICES)
    assert "S1: a woman's voice" in asked and "S2: a man's voice" in asked
    assert "When you write about a speaker yourself" in asked
    assert "never write the labels" in asked
