"""A cloud listener's drifted times are corrected by the words heard on this computer."""
from tarjim.asr.anchor import anchor
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

DRIFT = 9.0


def heard_at(text: str, start: float, step: float = 0.4) -> list[Word]:
    return [Word(w, start + k * step, start + k * step + 0.3)
            for k, w in enumerate(text.split())]


def test_a_drifted_sentence_moves_to_where_its_words_were_heard() -> None:
    said = "So I think the level of human intervention was vast"
    early = [Utterance(227.0, 231.0, "S1", said)]
    moved = anchor(early, heard_at(said, 227.0 + DRIFT), 250.0)
    assert abs(moved[0].start - (227.0 + DRIFT)) < 0.5
    assert moved[0].text == said


def test_a_short_reply_moves_with_its_drifted_neighbour() -> None:
    said = "It needs a lot of samples right"
    early = [Utterance(230.0, 233.0, "S1", said), Utterance(233.1, 233.5, "S2", "Mhm.")]
    moved = anchor(early, heard_at(said, 230.0 + DRIFT), 250.0)
    assert abs(moved[1].start - (233.1 + DRIFT)) < 0.5
    assert moved[1].speaker == "S2"


def test_small_differences_are_left_to_the_aligner() -> None:
    said = "Do you really believe that"
    on_time = [Utterance(8.0, 10.0, "S1", said)]
    assert anchor(on_time, heard_at(said, 8.6), 60.0) == on_time


def test_nothing_heard_locally_changes_nothing() -> None:
    lines = [Utterance(1.0, 2.0, "S1", "Hello there my friend")]
    assert anchor(lines, [], 60.0) == lines


def test_a_lone_common_word_does_not_drag_a_sentence() -> None:
    lines = [Utterance(10.0, 12.0, "S1", "Okay so here we go")]
    elsewhere = [Word("okay", 40.0, 40.3)]
    assert anchor(lines, elsewhere, 60.0) == lines


def test_a_move_never_passes_the_end_of_the_video() -> None:
    said = "right so it needed"
    late = [Utterance(240.0, 247.0, "S1", said)]
    moved = anchor(late, heard_at(said, 247.6), 248.5)
    assert moved[0].end <= 248.5
