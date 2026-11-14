"""Each speaker's voice is measured from the sound and told to whoever writes the lines
(2026-11-14: a man called Andrea was translated as a woman, from his name)."""
import numpy as np

from tarjim import post
from tarjim.asr import voices
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.prompt import Brief, build_prompt


def tone(hertz: float, seconds: float) -> np.ndarray:
    at = np.arange(int(seconds * voices.RATE)) / voices.RATE
    return (0.4 * np.sin(2 * np.pi * hertz * at)).astype(np.float32)


def talk(speaker: str, start: float, seconds: float) -> list[Word]:
    return [Word("word", start + k, start + k + 1.0, speaker) for k in range(int(seconds))]


def test_a_low_voice_and_a_high_one_are_told_apart_and_a_middle_one_is_left_unsaid() -> None:
    wav = np.concatenate([tone(110.0, 5.0), tone(220.0, 5.0), tone(168.0, 5.0)])
    words = [*talk("S1", 0.0, 5.0), *talk("S2", 5.0, 5.0), *talk("S3", 10.0, 5.0)]
    assert voices.measured(words, wav) == (("S1", "low"), ("S2", "high"))


def test_too_little_of_a_speaker_is_not_judged() -> None:
    wav = np.concatenate([tone(110.0, 2.0), tone(220.0, 6.0)])
    words = [*talk("S1", 0.0, 2.0), *talk("S2", 2.0, 6.0)]
    assert voices.measured(words, wav) == (("S2", "high"),)


def test_a_sound_that_cannot_be_read_stops_nothing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    broken = tmp_path / "clip.mp4"
    broken.write_bytes(b"not a video")
    assert voices.voices_of(broken, talk("S1", 0.0, 5.0)) == ()


def cue(text: str, speaker: str) -> Cue:
    return Cue(0.0, 3.0, [Word(text, 0.0, 3.0, speaker)])


def test_the_translator_is_told_each_voice_and_whose_line_each_slot_is() -> None:
    lines = [cue("Hi, I'm Andrea, a design principal.", "S1")]
    plain = build_prompt(lines, Brief(language("ar"), "msa", DEFAULT_RULES))
    told = build_prompt(lines, Brief(language("ar"), "msa", DEFAULT_RULES,
                                     voices=(("S1", "low"),)))
    assert "| S1]" in told and "S1: صوت رجل" in told and "من اسمه أبداً" in told
    assert "| S1]" not in plain and "صوت رجل" not in plain  # nothing known: asked as before
    english = build_prompt(lines, Brief(language("fr"), "", DEFAULT_RULES,
                                        voices=(("S1", "high"),)))
    assert "S1: a woman's voice (or a child's)" in english and "from a name" in english


def test_an_exchange_names_both_speakers_in_its_heading() -> None:
    first, second = [Word("Ready?", 0.0, 0.5, "S1")], [Word("Yes.", 0.6, 1.0, "S2")]
    exchange = Cue(0.0, 1.0, first + second, parts=[first, second])
    told = build_prompt([exchange], Brief(language("fr"), "", DEFAULT_RULES,
                                          voices=(("S1", "low"), ("S2", "high"))))
    assert "| A=S1 B=S2]" in told


def test_the_summary_is_told_the_voices_and_never_to_judge_from_a_name() -> None:
    asked = post.prompt("clip", language("ar"), ["أنا أندريا"], (("", "low"),))
    assert "the speaker: a man's voice" in asked and "from a name" in asked
    assert "a man's voice" not in post.prompt("clip", language("ar"), ["أنا أندريا"])
