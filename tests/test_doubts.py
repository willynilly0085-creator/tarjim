"""A finished job says which lines it is not sure of, in the three things a subtitle owes the
person: what was said was heard right, its meaning is the translation's, and it is on screen
while it is said (2026-11-14)."""
import json
from pathlib import Path
from typing import Any

from tarjim import doubts
from tarjim.doubts import Doubts, hearing_of, off_the_voice, reviewed
from tarjim.findings import Findings
from tarjim.models import Cue, Word
from tarjim.translate import faithful

AGREED: dict[str, Any] = {"backed": 3, "local": None, "source": "aligned", "score": 0.8}


def word(text: str, at: float, **facts: Any) -> Word:
    """A word every pass wrote and the aligner found, unless `facts` say otherwise."""
    return Word(text, at, at + 0.4, "S1", **{**AGREED, **facts})


def cue(words: list[Word], text: str = "ترجمة") -> Cue:
    return Cue(words[0].start, words[-1].end + 0.4, words, text)


def said(text: str, start: float = 0.0, **facts: Any) -> list[Word]:
    return [word(w, start + k * 0.5, **facts) for k, w in enumerate(text.split())]


def test_a_line_every_listener_agreed_on_is_not_doubted() -> None:
    assert hearing_of(cue(said("we met the banker there"))) is False


def test_a_line_a_third_of_whose_words_one_pass_wrote_stands_on_one_hearing() -> None:
    words = [*said("we met"), *said("the banker there", 1.0, backed=1)]
    assert hearing_of(cue(words)) is True


def test_one_small_word_alone_does_not_doubt_the_line() -> None:
    words = [*said("we met the banker"), word("uh", 2.0, backed=1), *said("there too", 2.5)]
    assert hearing_of(cue(words)) is False


def test_a_name_one_pass_alone_wrote_doubts_the_line_whatever_its_length() -> None:
    words = [*said("yesterday we met with"), word("Staley", 2.0, backed=1),
             *said("in the office downtown", 2.5)]
    assert hearing_of(cue(words)) is True


def test_a_number_one_pass_alone_wrote_doubts_the_line() -> None:
    words = [*said("he paid them about"), word("350", 2.0, backed=1),
             *said("million dollars that year", 2.5)]
    assert hearing_of(cue(words)) is True


def test_the_first_word_of_a_sentence_is_not_taken_for_a_name() -> None:
    words = [*said("we met there."), word("Then", 2.0, backed=1), *said("he left us", 2.5)]
    assert hearing_of(cue(words)) is False
    opening = [word("Then", 0.0, backed=1), *said("he left the room quietly", 0.5)]
    assert hearing_of(cue(opening)) is False


def test_the_listener_on_this_computer_clears_a_name_one_pass_wrote() -> None:
    words = [*said("we met with"), word("Staley", 2.0, backed=1, local=True)]
    assert hearing_of(cue(words)) is False


def test_a_line_with_nobody_to_ask_is_unknown_not_sure() -> None:
    assert hearing_of(cue(said("only one hearing", backed=None))) is None


def test_a_line_shown_long_after_its_first_word_is_off_the_voice() -> None:
    late = Cue(1.0, 3.0, said("this came up late"), "ترجمة")
    assert off_the_voice(late, 0.3) and not off_the_voice(cue(said("on time")), 0.3)


def test_a_line_gone_before_its_last_word_is_off_the_voice() -> None:
    assert off_the_voice(Cue(0.0, 1.0, said("gone before the end of it"), "ترجمة"), 0.3)


def test_a_line_whose_first_word_was_given_a_guessed_time_is_off_the_voice() -> None:
    words = [word("guessed", 0.0, source="estimated"), *said("then found", 0.5)]
    assert off_the_voice(cue(words), 0.3)


def test_a_line_whose_letters_are_not_in_the_sound_there_is_off_the_voice() -> None:
    assert off_the_voice(cue(said("not found where timed", score=0.05)), 0.3)
    assert not off_the_voice(cue(said("a stand-in has no ears", score=None)), 0.3)


def test_the_review_keeps_each_line_with_its_doubts(tmp_path: Path) -> None:
    lines = [cue(said("we met the banker there")),
             cue([*said("he paid", 10.0), word("350", 11.0, backed=1)], "دفع 350"),
             cue(said("nobody to ask", 20.0, backed=None)),
             Cue(31.0, 33.0, said("this came up late", 30.0), "ترجمة")]
    found = reviewed(tmp_path / "cues.ar.json", lines, ())
    assert found == Doubts(4, hearing=(2,), unheard=1, meaning=(), timing=(4,))
    rows = json.loads((tmp_path / "cues.ar.json").read_text(encoding="utf-8"))
    assert [row["doubts"] for row in rows] == [[], ["hearing"], [], ["timing"]]
    assert rows[1]["source"] == "he paid 350" and rows[1]["text"] == "دفع 350"


def test_the_log_says_the_three_in_one_line() -> None:
    line = Doubts(40, hearing=(2, 9), unheard=3, meaning=(5,), timing=()).said()
    assert line == ("report: of 40 line(s), 2 stand on one hearing (3 with nobody to ask), "
                    "1 translation(s) to check, 0 not surely on the voice")


def test_the_job_lists_its_doubts_quietly() -> None:
    lines = [cue(said(f"line {n}", n * 10.0)) for n in range(4)]
    found = Findings(doubts=Doubts(4, hearing=(2,), meaning=(3, 1), timing=(4,)), in_source=[1])
    notes = {note["kind"]: note for note in found.notes(lines, [])}
    assert notes["hearing_doubt"] == {"kind": "hearing_doubt", "problem": False, "count": 1,
                                      "at": [10.0]}
    assert notes["meaning_doubt"]["at"] == [20.0]  # line 1 is already listed as left as said
    assert notes["timing_doubt"]["at"] == [30.0] and "hearing_unchecked" not in notes


def test_a_job_nobody_could_check_says_so() -> None:
    lines = [cue(said("one hearing", backed=None))]
    notes = Findings(doubts=Doubts(1, unheard=1)).notes(lines, [])
    assert notes == [{"kind": "hearing_unchecked", "problem": False, "count": 1, "at": []}]
    assert Findings(doubts=Doubts(0)).notes([], []) == []


def test_meaning_is_asked_of_the_translation_checks() -> None:
    lines = [cue(said("in 2019 he left")), cue(said("fine", 5.0))]
    assert doubts.found(lines, ()).meaning == tuple(faithful.unfaithful(lines, ()))
