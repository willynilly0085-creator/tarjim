"""A line a listener put past its piece is no longer dropped whole (2026-11-08): an mm:ss misread
("1:05" written as 105 s) is read back as minutes and seconds, a line said nowhere else in the
piece is kept at the piece's edge with no trust in its time, and only a copy of a line the piece
already has is dropped, as a listener's invention."""
import pytest

from tarjim import guards
from tarjim.listen.chunks import OVERRUN, SHORTEST, shift
from tarjim.listen.gemini_listen import Utterance as U

PIECE = (100.0, 175.0)  # 75 s long


@pytest.fixture(autouse=True)
def counting() -> None:
    guards.reset()


def count(name: str) -> int:
    return guards.counts().get(name, 0)


def test_a_line_inside_its_piece_moves_as_before() -> None:
    [line] = shift([U(10.0, 12.0, "S1", "inside")], PIECE, tag="t", request="k0.v")
    assert (line.start, line.end, line.speaker, line.text) == (110.0, 112.0, "tS1", "inside")
    assert (line.piece, line.request, line.prior) == (PIECE, "k0.v", 1.0)
    [late] = shift([U(74.5, 80.0, "S1", "runs over")], PIECE)
    assert (late.start, late.end) == (174.5, 175.0 + OVERRUN)


def test_a_line_a_minute_past_its_piece_is_kept_inside_it_with_no_trust() -> None:
    lines = [U(5.0, 7.0, "S1", "first words here"), U(135.0, 138.0, "S1", "lost words there")]
    kept = shift(lines, PIECE)
    assert [u.text for u in kept] == ["first words here", "lost words there"]
    clamped = kept[1]
    assert PIECE[0] - OVERRUN <= clamped.start < clamped.end <= PIECE[1] + OVERRUN
    assert clamped.end - clamped.start >= SHORTEST - 1e-9 and clamped.prior == 0.0
    assert count("shift.clamped") == 1 and count("shift.hallucinated") == 0


def test_an_mm_ss_misread_is_read_back_as_minutes_and_seconds() -> None:
    lines = [U(50.0, 55.0, "S1", "before the minute"), U(105.0, 108.5, "S2", "at one oh five"),
             U(110.0, 114.0, "S1", "at one ten")]
    kept = shift(lines, PIECE)
    assert [(u.start, u.end, u.prior) for u in kept[1:]] == [
        (165.0, 168.5, 0.5), (170.0, 174.0, 0.5)]
    assert count("shift.slipped") == 2


def test_a_misread_that_would_break_the_lines_order_is_not_trusted() -> None:
    lines = [U(70.0, 73.0, "S1", "near the end"), U(105.0, 107.0, "S2", "said somewhere else")]
    kept = shift(lines, PIECE)
    assert kept[1].prior == 0.0 and kept[1].start > 170.0
    assert count("shift.slipped") == 0 and count("shift.clamped") == 1


def test_a_copy_of_a_line_the_piece_has_past_its_end_is_dropped() -> None:
    lines = [U(10.0, 14.0, "S1", "thank you all for coming tonight"),
             U(90.0, 94.0, "S1", "thank you all for coming tonight!")]
    kept = shift(lines, PIECE)
    assert [u.start for u in kept] == [110.0]
    assert count("shift.hallucinated") == 1


def test_two_copies_past_the_end_keep_one() -> None:
    lines = [U(80.0, 82.0, "S1", "something new"), U(83.0, 85.0, "S1", "something new")]
    assert len(shift(lines, PIECE)) == 1
    assert count("shift.clamped") == 1 and count("shift.hallucinated") == 1


def test_a_line_whose_time_is_not_known_is_held_back_from_the_timing() -> None:
    from tarjim.listen.chunks import placeable

    lines = shift([U(5.0, 7.0, "S1", "first words here"), U(105.0, 108.0, "S2", "read back"),
                   U(170.0, 172.0, "S1", "lost words there")], PIECE)
    assert [u.text for u in placeable(lines)] == ["first words here", "read back"]
    assert count("shift.held") == 1


def test_a_misread_that_lands_inside_the_line_before_is_not_trusted() -> None:
    lines = [U(68.0, 69.8, "S1", "thank you for your patience"), U(109.0, 110.0, "S2", "no")]
    kept = shift(lines, PIECE)
    assert kept[1].prior == 0.0 and count("shift.slipped") == 0
