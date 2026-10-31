"""The pieces of the check after alignment: piles, what counts as said already, spreading."""
from tarjim.asr.piles import piles, spread
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.novel import said_before, timed_over
from tarjim.models import Word


def words_at(ends: list[float]) -> list[Word]:
    return [Word(f"w{i}", end - 0.2, end) for i, end in enumerate(ends)]


def test_words_said_at_a_speaking_pace_are_no_pile() -> None:
    assert piles(words_at([0.3 * k for k in range(40)])) == []


def test_words_ending_at_one_instant_are_a_pile() -> None:
    ends = [1.0, 1.4, *[5.0] * 6, 5.5, 5.9]
    assert piles(words_at(ends)) == [(2, 8)]


def test_a_few_words_close_together_are_no_pile() -> None:
    assert piles(words_at([1.0, 1.05, 1.1, 1.4])) == []


def test_spread_keeps_every_word_in_order_inside_the_speech() -> None:
    pile = [Word(t, 5.0, 5.0) for t in ["one", "two", "three", "four", "five", "six"]]
    out = spread(pile, (0.0, 10.0), [(1.0, 3.0), (6.0, 8.0)])
    assert [w.text for w in out] == [w.text for w in pile]
    assert out[0].start == 1.0 and abs(out[-1].end - 8.0) < 1e-9
    assert all(not 3.0 < w.start < 6.0 for w in out)  # nobody starts in the pause


def test_spread_without_known_speech_uses_the_whole_span() -> None:
    out = spread([Word("a", 4, 4), Word("b", 4, 4)], (2.0, 4.0), [])
    assert out[0].start == 2.0 and abs(out[-1].end - 4.0) < 1e-9


def test_a_left_out_sentence_is_not_taken_for_a_long_line_sharing_its_common_words() -> None:
    long_line = Utterance(452.2, 531.7, "S1", "The first thing I mean is that President Trump and "
                          "his people did the first term his way, and the inner team did not")
    heard = Utterance(519.6, 524.2, "S1", "The first Trump presidency. I mean, did President "
                      "Trump and his inner circle?")
    assert not said_before(heard, [long_line])


def test_a_line_already_said_nearby_is_old() -> None:
    line = Utterance(60.0, 70.0, "S1", "we can help set the context our leaders will tackle")
    again = Utterance(68.0, 71.0, "S1", "our leaders will tackle")
    assert said_before(again, [line])


def test_a_line_whose_time_timed_words_fill_is_old() -> None:
    line = Utterance(10.0, 12.0, "S1", "x")
    assert timed_over(line, [(9.5, 11.5)]) and not timed_over(line, [(11.5, 13.0)])
