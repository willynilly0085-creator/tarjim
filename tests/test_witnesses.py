"""Each word shown carries who else wrote it there: how many of the listening passes, and whether
the listener on this computer did. A word one pass alone heard no longer looks like one every
listener agreed on (2026-11-14)."""
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.witness import NEAR, alone, witnessed
from tarjim.models import Word


def timed(text: str, start: float = 0.0, step: float = 0.5) -> list[Word]:
    return [Word(word, start + k * step, start + (k + 1) * step, "S1")
            for k, word in enumerate(text.split())]


def line(text: str, start: float = 0.0, end: float = 5.0) -> Utterance:
    return Utterance(start, end, "S1", text)


def test_a_word_every_pass_wrote_is_backed_by_all_of_them() -> None:
    passes = [[line("we met Jes Staley there")]] * 3
    words = witnessed(timed("we met Jes Staley there"), passes, [])
    assert [w.backed for w in words] == [3] * 5
    assert all(w.local is None for w in words)  # nobody on this computer listened


def test_a_name_one_pass_alone_wrote_is_backed_by_one() -> None:
    passes = [[line("we met Jes Staley there")], [line("we met Jess Daily there")],
              [line("we met just daily there")]]
    words = witnessed(timed("we met Jes Staley there"), passes, [])
    assert [w.backed for w in words] == [3, 3, 1, 1, 3]
    assert [alone(w) for w in words] == [False, False, True, True, False]


def test_the_listener_on_this_computer_vouches_for_a_word_one_pass_wrote() -> None:
    passes = [[line("we met Jes Staley there")], [line("we met there")], [line("we met there")]]
    words = witnessed(timed("we met Jes Staley there"), passes, timed("we met Jes Staley there"))
    assert all(w.local for w in words)
    assert not any(alone(w) for w in words)


def test_the_same_word_said_far_away_is_no_witness() -> None:
    far = 2 * NEAR + 60.0
    passes = [[line("hello there")], [line("hello there", far, far + 5)],
              [line("hello there", far, far + 5)]]
    words = witnessed(timed("hello there"), passes, [])
    assert [w.backed for w in words] == [1, 1]


def test_one_pass_and_no_listener_here_leaves_nothing_to_ask() -> None:
    words = witnessed(timed("only one hearing"), [[line("only one hearing")]], [])
    assert all(w.backed is None and w.local is None for w in words)
    assert all(alone(w) is None for w in words)


def test_a_mark_with_no_letters_is_not_judged() -> None:
    passes = [[line("yes - no")]] * 3
    words = witnessed(timed("yes - no"), passes, timed("yes no"))
    assert words[1].backed is None and words[1].local is None
    assert alone(words[1]) is None


def test_a_line_only_asking_again_brought_stands_on_that_one_hearing() -> None:
    passes = [[line("first line")]] * 3
    again = [line("later fill", 30.0, 31.0)]
    words = witnessed([*timed("first line"), *timed("later fill", 30.0)], passes, [], again)
    assert [w.backed for w in words] == [3, 3, 1, 1]
    assert [alone(w) for w in words] == [False, False, True, True]
    heard_here = witnessed(words, passes, timed("later fill", 30.0), again)
    assert not any(alone(w) for w in heard_here[2:])  # the listener here heard it too


def test_a_line_only_the_listener_here_filled_in_is_no_witness_to_itself() -> None:
    passes = [[line("first line")]] * 3
    local = [*timed("first line"), *timed("local fill", 30.0)]
    words = witnessed([*timed("first line"), *timed("local fill", 30.0)], passes, local)
    assert [w.backed for w in words] == [3, 3, 0, 0] and all(w.local for w in words)
    assert [alone(w) for w in words] == [False, False, True, True]


def test_one_pass_and_the_listener_here_are_two_hearings() -> None:
    words = witnessed(timed("we met Staley"), [[line("we met Staley")]], timed("we met daily"))
    assert [w.backed for w in words] == [1, 1, 1]
    assert [alone(w) for w in words] == [False, False, True]


def test_a_long_clip_is_matched_stretch_by_stretch() -> None:
    text = " ".join(f"word{k}" for k in range(900))
    words = timed(text)
    lines = [Utterance(k * 5.0, k * 5.0 + 5.0, "S1", " ".join(f"word{n}" for n in
                                                              range(k * 10, k * 10 + 10)))
             for k in range(90)]
    found = witnessed(words, [lines, lines, lines[:45]], [])
    assert [w.backed for w in found[:450]] == [3] * 450
    assert all(w.backed == 2 for w in found[450:])


def test_words_keep_their_order_when_two_voices_cross() -> None:
    words = [Word("yes", 3.0, 3.4, "S2"), *timed("one two three four")]
    passes = [[line("one two three four"), Utterance(3.0, 3.4, "S2", "yes")]] * 3
    found = witnessed(words, passes, [])
    assert [w.text for w in found] == ["yes", "one", "two", "three", "four"]
    assert all(w.backed == 3 for w in found)
