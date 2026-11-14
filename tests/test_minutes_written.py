"""A pass whose listener wrote its times past the first minute as minutes and seconds without
the colon (1:09 as 109) is read back whole, before the passes are voted (2026-11-14: two such
passes of three cost a 96-second clip its last third)."""
import pytest

from tarjim import guards
from tarjim.listen.chunks import joined, listen_in_chunks, placed_in
from tarjim.listen.gemini_listen import Utterance as U
from tarjim.listen.merge import Heard, Piece, agreed

LENGTH = 96.0
SAID = [(0.0, 33.0, "S1", "we begin with a long opening turn about the garden and the tools"),
        (33.4, 34.0, "S2", "Mhm."),
        (34.0, 48.6, "S1", "then the seeds go in rows and the water follows every morning"),
        (48.9, 59.3, "S2", "so you think the frost is the reason nothing came up this year"),
        (59.3, 69.1, "S1", "correct yes the frost and I mean the whole valley had it"),
        (69.1, 69.9, "S2", "Right."),
        (69.9, 80.2, "S1", "we saw the neighbour lose his plums and the school its beans"),
        (81.3, 86.4, "S1", "you did have a few farms that covered everything in time"),
        (87.3, 92.1, "S1", "nobody else was ready and the market stayed empty for weeks"),
        (93.8, 96.2, "S1", "we will see what is left by next week")]


@pytest.fixture(autouse=True)
def counting() -> None:
    guards.reset()


def colonless(seconds: float) -> float:
    """The time as a listener writes it in minutes and seconds with the colon left out."""
    return round(100.0 * (seconds // 60) + seconds % 60, 2)


def run(shift: float = 0.0, written: bool = False) -> list[U]:
    """The lines as one pass heard them, `shift` seconds off, its times written so or not."""
    as_written = colonless if written else float
    return [U(as_written(a + shift), as_written(b + shift), who, text) for a, b, who, text in SAID]


def close(lines: list[U], reach: float = 1.0) -> bool:
    return len(lines) == len(SAID) and all(
        abs(u.start - a) <= reach and abs(u.end - b) <= reach and u.text == text
        for u, (a, b, _, text) in zip(lines, SAID, strict=True))


def test_a_pass_written_in_minutes_and_seconds_is_read_back_whole() -> None:
    placed = placed_in(run(written=True), LENGTH)
    assert close(placed, reach=0.01)
    assert all(u.prior > 0.0 for u in placed)
    assert guards.counts().get("shift.minutes", 0) == 1
    assert guards.counts().get("shift.clamped", 0) == 0


def test_the_line_said_over_the_minute_ends_where_it_was_said() -> None:
    """Its start is under a minute and reads as it is; its end is 1:09 written 109. It ran to
    the piece's end and no line after it could be read back."""
    over = next(u for u in placed_in(run(written=True), LENGTH) if u.start == 59.3)
    assert (over.end, over.prior) == (69.1, 1.0)


def test_two_passes_written_so_do_not_outvote_the_one_that_is_right() -> None:
    piece = Piece(0.0, LENGTH, [run(), run(-0.4, written=True), run(0.3, written=True)])
    lines, passes = joined([piece])
    assert close(lines) and all(u.prior > 0.0 for u in lines)
    assert all(close(heard) for heard in passes)


def test_a_fresh_hearing_keeps_its_first_piece_read_back() -> None:
    runs = [run(), run(-0.4, written=True), run(0.3, written=True)]
    heard = listen_in_chunks(LENGTH, [], lambda _a, _b: Heard("English", agreed(runs), runs))
    assert close(heard.utterances)
    assert max(u.end for kept in heard.pieces[0].passes for u in kept) <= LENGTH + 1.0


def test_a_pass_with_a_time_between_one_minute_and_a_hundred_seconds_is_left_as_heard() -> None:
    """Such a time cannot be minutes and seconds: the pass is in seconds."""
    lines = [U(50.0, 58.0, "S1", "a line before the minute"),
             U(64.0, 70.0, "S2", "a line in seconds after it"),
             U(101.0, 104.0, "S1", "a line past a hundred seconds")]
    assert [(u.start, u.end) for u in placed_in(lines, 110.0)] == [
        (50.0, 58.0), (64.0, 70.0), (101.0, 104.0)]
    assert guards.counts().get("shift.minutes", 0) == 0


def test_in_a_long_request_a_slow_line_over_the_minute_is_not_read_back() -> None:
    """A request longer than 100 s can hold such times as they stand. A line of 600 letters
    said from 56 s to 101 s lasts 45 s as it stands and 5 s read back: neither is impossible, and
    45 s is the nearer to its words."""
    long_turn = " ".join(["unhurried"] * 60)
    lines = [U(20.0, 30.0, "S1", "the opening words of the piece"),
             U(56.0, 101.0, "S1", long_turn), U(103.0, 108.0, "S2", "and a reply after it")]
    assert [(u.start, u.end) for u in placed_in(lines, 110.0)] == [
        (20.0, 30.0), (56.0, 101.0), (103.0, 108.0)]


def test_in_a_long_request_a_quick_line_over_the_minute_is_read_back() -> None:
    lines = [U(20.0, 30.0, "S1", "the opening words of the piece"),
             U(56.0, 101.5, "S1", "a short line said in a few seconds"),
             U(103.0, 108.0, "S2", "and a reply after it")]
    assert [(u.start, u.end) for u in placed_in(lines, 110.0)] == [
        (20.0, 30.0), (56.0, 61.5), (63.0, 68.0)]


def test_one_line_ending_past_its_piece_is_read_back_when_the_rest_is_in_seconds() -> None:
    """Not the whole pass: one end. It no longer runs to the edge and walls off what follows."""
    lines = [U(40.0, 55.0, "S1", "a line wholly before the minute"),
             U(57.0, 104.0, "S2", "this one ends at one oh four"),
             U(66.0, 70.0, "S1", "and this one is in plain seconds")]
    kept = placed_in(lines, 75.0)
    assert [(u.start, u.end) for u in kept] == [(40.0, 55.0), (57.0, 64.0), (66.0, 70.0)]


def test_in_a_long_request_forty_seconds_of_nothing_are_left_as_heard() -> None:
    """Found in review, 2026-11-14: with no line over the minute to judge by, a pass that was
    right (music from 57 s to 101 s) was read back and its last lines put 40 s early."""
    lines = [U(20.0, 30.0, "S1", "the opening words of the piece"),
             U(50.0, 57.0, "S1", "the last words before the music"),
             U(101.5, 105.0, "S2", "the first words after it"),
             U(106.0, 110.0, "S1", "and the closing line")]
    assert [(u.start, u.end) for u in placed_in(lines, 112.0)][2:] == [
        (101.5, 105.0), (106.0, 110.0)]
    assert guards.counts().get("shift.minutes", 0) == 0


def test_another_pass_that_heard_speech_there_says_the_pass_was_written_so() -> None:
    from tarjim.listen.minutes import read_back_all

    said = [(20.0, 30.0, "the opening words of the piece"),
            (50.0, 57.0, "the last words before the minute"),
            (61.5, 65.0, "the first words after it"), (66.0, 70.0, "and the closing line")]
    right = [U(a, b, "S1", text) for a, b, text in said]
    written = [U(colonless(a), colonless(b), "S1", text) for a, b, text in said]
    again = read_back_all([right, written], 112.0)
    assert [(u.start, u.end) for u in again[1]] == [(a, b) for a, b, _ in said]
    assert again[0] == right

