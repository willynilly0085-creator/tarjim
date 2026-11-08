"""A long labelled turn begun well before another voice's turn ends gives the words it says
over that turn as a reply, and keeps the rest on the main track (2026-11-08)."""
from tarjim.models import Word
from tarjim.tracks import tracks

HOST = [Word(t, 1.0 + k, 1.8 + k, "S1") for k, t in enumerate(["a", "b", "c", "d."])]


def test_a_long_turn_said_over_another_gives_only_its_words_said_over_as_a_reply() -> None:
    over = [Word(f"word{k}", 3.0 + 0.5 * k, 3.4 + 0.5 * k, "S2") for k in range(20)]
    main, replies = tracks([*HOST, *over])
    assert replies == [over[:4]]  # 3.0 to 4.5 s, said while "d." is said
    assert main == [*HOST, *over[4:]]


def test_a_long_turn_that_fits_a_line_is_a_reply_whole() -> None:
    over = [Word(t, 4.2 + 0.4 * k, 4.5 + 0.4 * k, "S2") for k, t in enumerate(
        ["That", "is", "far", "too", "simple."])]
    main, replies = tracks([*HOST, *over])
    assert replies == [over] and main == HOST


def test_a_turn_begun_just_before_the_last_one_ends_stays_on_the_main_track() -> None:
    over = [Word(f"word{k}", 4.5 + 0.5 * k, 4.9 + 0.5 * k, "S2") for k in range(6)]
    for words in ([*HOST, *over], [Word(w.text, w.start, w.end, "S1") for w in [*HOST, *over]],
                  [Word(w.text, w.start, w.end) for w in [*HOST, *over]]):
        main, replies = tracks(words)
        assert replies == [] and main == words
