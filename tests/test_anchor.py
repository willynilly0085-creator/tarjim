"""A cloud listener's drifted times are corrected by the words heard on this computer."""
from tarjim.asr.anchor import UNKNOWN, anchor
from tarjim.listen.chunks import CLAMPED
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


def test_a_line_stretched_to_its_pieces_end_keeps_its_place() -> None:
    # 2026-11-08: a line said in 133-147 s came back as 131-164 s; moving it by the median of
    # its words put it ahead of the turn said before it
    said = ("your statements are also shockingly ahistorical in another respect which is if you "
            "look at the history of immigration it has actually ebbed and flowed")
    turn = Utterance(123.7, 132.6, "S2", "you're bringing a press one for English philosophy")
    stretched = Utterance(131.4, 164.4, "S1", said)
    heard = [*heard_at(turn.text, 127.0), *heard_at(said, 133.2, 0.5)]
    moved = anchor([turn, stretched], heard, 410.0)
    assert moved[1].start == stretched.start and moved[0].start < moved[1].start
    last = heard[-1].end
    assert last < moved[1].end <= last + 1.0  # its end where its words end, not at 164 s


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


def test_a_line_of_unknown_time_neither_moves_nor_moves_its_neighbours() -> None:
    """2026-11-09, en_long_seven slip: a line the listener put a minute late, past its piece, is
    kept at the piece's edge with no trust in its time (chunks.CLAMPED). Its words matched the
    local words where it was said, 9 s before the edge, and the lines before it, whose own local
    words the sound had not confirmed, borrowed that 9 s: shown over the turn before them, with
    the stretch they were said in asked again and heard twice."""
    assert UNKNOWN == CLAMPED
    edge = Utterance(64.43, 64.73, "S2", "The first version got stuck halfway every single time.",
                     prior=CLAMPED)
    lines = [Utterance(58.6, 59.2, "S3", "Every time."),
             Utterance(59.95, 61.36, "S2", "We had to push it with a broom."), edge]
    moved = anchor(lines, heard_at(edge.text, 55.5), 400.0)
    assert moved == lines
    assert [u.prior for u in moved] == [1.0, 1.0, 0.0]
