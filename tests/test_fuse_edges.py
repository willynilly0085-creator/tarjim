"""Unheard words at either end of a retimed line stay inside the room the line may take: the line
it was said in and the turns around it. On 2026-11-08 they were first given a fixed length past
the heard words, which crossed a close neighbour, so the retime was refused and the line stayed
seconds away where the aligner had put it."""
from tarjim.asr.fuse import fill, fuse
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word


def aligned_at(line: Utterance, start: float, step: float) -> list[Word]:
    words = line.text.split()
    return [Word(w, start + k * step, start + (k + 1) * step, line.speaker)
            for k, w in enumerate(words)]


def test_an_unheard_last_word_before_a_close_turn_still_lets_the_line_move() -> None:
    lines = [Utterance(10.0, 10.8, "S1", "one two three"),
             Utterance(10.8, 12.0, "S2", "a b c d e")]
    words = aligned_at(lines[0], 20.0, 0.35) + aligned_at(lines[1], 10.8, 0.2)
    heard = [Word("one", 10.0, 10.3), Word("two", 10.4, 10.7)]
    fused = fuse(words, lines, heard)[:3]
    assert fused[0].start == 10.0 and fused[1].start == 10.4
    assert fused[2].start >= 10.7 and fused[2].end <= 10.8


def test_unheard_first_words_after_a_close_turn_still_let_the_line_move() -> None:
    lines = [Utterance(8.0, 9.9, "S2", "a b c"),
             Utterance(10.0, 11.0, "S1", "uh well one two three")]
    words = aligned_at(lines[0], 8.0, 0.6) + aligned_at(lines[1], 20.0, 0.9)
    heard = [Word("one", 10.0, 10.3), Word("two", 10.3, 10.6), Word("three", 10.6, 10.9)]
    fused = fuse(words, lines, heard)[3:]
    assert fused[0].start >= 9.9 and fused[-1].end == 10.9
    assert fused[2].start == 10.0


def test_edge_words_share_only_the_room_they_have() -> None:
    spans = fill(["uh", "well", "one", "two"], [None, None, (10.0, 10.3), None], (9.5, 10.4))
    assert spans[0][0] >= 9.5 and spans[1][1] == 10.0 and spans[0][1] > spans[0][0]
    assert spans[-1] == (10.3, 10.4)
    assert fill(["a", "b"], [(5.0, 5.2), None], (4.0, 5.1)) == [(5.0, 5.2), (5.2, 5.2)]
