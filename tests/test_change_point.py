"""Since 2026-11-09 a label whose voice changes from some point on (the listener swapped host and
guest after a pause, 2026-11-06) is split there and each part goes to its own voice; one window
heard nearer the wrong voice neither makes a change nor hides one, and the cut is the widest pause
between the two lines, so short lines between them go with the side they are said on."""
import numpy as np
import pytest
from fake_voices import Turn, by_turns, end, heard, people, relabelled, sound, spoken

from tarjim.listen import whose
from tarjim.listen.changes import changes, cut
from tarjim.listen.turns import Window

NOTHING = np.zeros(1)


def windows_of(lines: list[int]) -> list[Window]:
    """One 2 s window a second, each in the line given."""
    return [Window((line, line + 1), k * 1.0, k * 1.0 + 2.0, "S1", NOTHING)
            for k, line in enumerate(lines)]


def test_a_voice_that_changes_between_two_lines_is_a_change() -> None:
    order = windows_of([0, 0, 0, 1, 1, 1, 2, 2, 2])
    assert changes(order, [0, 0, 0, 0, 0, 0, 1, 1, 1]) == [6]


def test_one_window_heard_nearer_the_wrong_voice_neither_makes_nor_hides_a_change() -> None:
    order = windows_of([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    assert changes(order, [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]) == []
    assert changes(order, [0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 1]) == [6]


def test_two_windows_of_another_voice_are_no_change() -> None:
    order = windows_of([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    assert changes(order, [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0]) == []


def test_a_voice_changes_only_at_a_pause() -> None:
    # a turn run on into the next person's under one label is cut at the pause between them
    ids = [0, 0, 0, 0, 1, 1, 1, 1]
    assert changes(windows_of([0] * 8), ids) == [4]
    assert changes(windows_of([0] * 8), ids, lambda _at: False) == []


def test_a_label_changes_voice_twice_at_most() -> None:
    order = windows_of([k // 2 for k in range(16)])
    ids = [0] * 4 + [1] * 4 + [0] * 4 + [1] * 4
    # three changes as clear as each other: the first two are kept
    assert changes(order, ids) == [4, 8]


def test_the_cut_is_the_widest_pause_between_the_two_lines() -> None:
    spans = [(0.0, 2.0), (2.5, 3.0), (5.0, 5.4), (5.6, 8.0)]
    assert cut(spans, 0.0, 5.6) == pytest.approx(4.0)


def test_a_label_swapped_from_a_point_on_is_split_there_and_put_right(
        monkeypatch: pytest.MonkeyPatch) -> None:
    turns = by_turns(20, "AB")
    swapped = relabelled(turns, {k: "S2" if t.voice == "A" else "S1"
                                 for k, t in enumerate(turns) if k >= 12})
    words = heard(monkeypatch, swapped, people("AB"))
    after = whose.checked(words, sound(end(turns)))
    assert spoken(after, swapped) == [t.label for t in turns]


def test_a_short_reply_after_the_swap_goes_with_its_side(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the guest's "Right." 0.1 s after the host's turn 14, heard as the host's like every guest
    # line from turn 12 on: line by line it was too short to move (2026-11-09 bench)
    turns = by_turns(20, "AB")
    swapped = relabelled(turns, {k: "S2" if t.voice == "A" else "S1"
                                 for k, t in enumerate(turns) if k >= 12})
    reply = Turn(turns[14].start + 4.1, 0.4, "B", "S1")
    words = heard(monkeypatch, [*swapped, reply], people("AB"))
    after = whose.checked(words, sound(end(turns)))
    assert next(w.speaker for w in after if w.start == reply.start) == "S2"
    assert spoken(after, swapped) == [t.label for t in turns]


def test_labels_already_right_are_never_split(monkeypatch: pytest.MonkeyPatch) -> None:
    for seed in range(6):
        turns = by_turns(20, "AB")
        words = heard(monkeypatch, turns, people("AB", seed))
        assert whose.checked(words, sound(end(turns))) == words



def test_a_short_line_before_the_change_goes_with_the_voice_it_sounds_like(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the host's 1.2 s "Let us talk about cost." is the last line before the swap; the widest
    # pause of the host's label is before it, where the guest talks (2026-11-09 bench)
    talk = [Turn(0, 4, "A", "S1"), Turn(5, 4, "B", "S2"), Turn(10, 4, "A", "S1"),
            Turn(15, 4, "B", "S2"), Turn(20, 4, "A", "S1"), Turn(25, 4, "B", "S2"),
            Turn(38, 1.2, "A", "S1"), Turn(40.5, 4, "B", "S1"), Turn(46, 4, "A", "S2"),
            Turn(51, 4, "B", "S1"), Turn(56, 4, "A", "S2"), Turn(61, 4, "B", "S1"),
            Turn(66, 4, "A", "S2")]
    words = heard(monkeypatch, talk, people("AB"))
    after = spoken(whose.checked(words, sound(end(talk))), talk)
    assert after == ["S1" if t.voice == "A" else "S2" for t in talk]


def test_a_swap_in_a_label_heard_only_in_short_lines_before_it_is_still_undone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the guest answers in 1.2 s lines, too short for a window, until the labels swap: each is
    # glimpsed once, so the guest's label still changes voice there (2026-11-09 bench)
    talk: list[Turn] = []
    for k in range(14):
        host, guest = ("S1", "S2") if k < 7 else ("S2", "S1")
        talk += [Turn(k * 10.0, 4.0, "A", host),
                 Turn(k * 10.0 + 4.6, 1.2 if k < 7 else 4.0, "B", guest)]
    words = heard(monkeypatch, talk, people("AB"))
    after = spoken(whose.checked(words, sound(end(talk))), talk)
    assert len({name for name, t in zip(after, talk, strict=True) if t.voice == "A"}) == 1
    assert len({name for name, t in zip(after, talk, strict=True) if t.voice == "B"}) == 1
    assert after[0] != after[1]


def test_a_short_line_goes_where_its_labels_lines_on_both_sides_went(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the guest's label has two lines of one window each before the swap, too few to see it
    # change voice; both are moved by their own voice, so "Sugar in soup?" between them goes
    # with them (2026-11-09 bench)
    talk = [Turn(0, 5, "A", "S1"), Turn(5.6, 2.1, "B", "S2"), Turn(8.3, 5, "A", "S1"),
            Turn(13.9, 0.6, "B", "S2"), Turn(15.1, 5, "A", "S1"), Turn(20.7, 2.1, "B", "S2")]
    for k in range(6):
        talk += [Turn(24.0 + k * 9.6, 4.0, "A", "S2"), Turn(28.6 + k * 9.6, 4.0, "B", "S1")]
    words = heard(monkeypatch, talk, people("AB"))
    after = spoken(whose.checked(words, sound(end(talk))), talk)
    assert len({name for name, t in zip(after, talk, strict=True) if t.voice == "B"}) == 1


def test_a_swap_is_one_moment_for_both_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    # the host's "Slow down?", "And?" and "Right." come after the swap, short, under the
    # guest's old label: the host's label changes voice before the guest's next turn, so they
    # are cut after the swap too, not kept with the guest (2026-11-09 bench)
    talk = [Turn(k * 9.2, 4.0, "A", "S1") for k in range(5)]
    talk += [Turn(k * 9.2 + 4.6, 4.0, "B", "S2") for k in range(5)]
    talk += [Turn(46.4, 0.5, "A", "S2"), Turn(47.5, 4.0, "B", "S1"), Turn(52.1, 0.6, "A", "S2"),
             Turn(53.3, 4.0, "B", "S1"), Turn(57.9, 0.5, "A", "S2")]
    for k in range(4):
        talk += [Turn(59.6 + k * 9.2, 4.0, "A", "S2"), Turn(64.2 + k * 9.2, 4.0, "B", "S1")]
    assert one_name_each(monkeypatch, talk, "AB")


def one_name_each(monkeypatch: pytest.MonkeyPatch, talk: list[Turn], voices: str) -> bool:
    """Whether each voice's turns all end up under one name, the names all different."""
    talk.sort(key=lambda t: t.start)
    words = heard(monkeypatch, talk, people(voices))
    after = spoken(whose.checked(words, sound(end(talk))), talk)
    found = [{name for name, t in zip(after, talk, strict=True) if t.voice == v} for v in voices]
    return all(len(names) == 1 for names in found) and len(set.union(*found)) == len(voices)


def test_a_short_first_line_after_the_swap_goes_with_its_side(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # A's 0.5 s line opens the swap under B's old label just after C talks, run on into A's
    # next line (0.9 s pause): that label's pause where the swap is began at B's last line,
    # before the window A's label leaves for the change, and was not looked at (2026-11-09
    # bench, en_fourth_voice seed 1)
    talk = [Turn(k * 13.8 + d, 4.0, v, s) for k in range(3)
            for d, v, s in ((0.0, "A", "S1"), (4.6, "B", "S2"), (9.2, "C", "S3"))]
    talk += [Turn(41.4, 4.0, "A", "S1"), Turn(46.0, 4.0, "C", "S3"),
             Turn(50.6, 0.5, "A", "S2"), Turn(52.0, 4.0, "A", "S2")]
    talk += [Turn(56.9 + k * 13.8 + d, 4.0, v, s) for k in range(4)
             for d, v, s in ((0.0, "B", "S1"), (4.6, "C", "S3"), (9.2, "A", "S2"))]
    assert one_name_each(monkeypatch, talk, "ABC")


def test_a_short_reply_just_after_the_swap_is_not_kept_with_the_turn_before(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # B's 0.44 s "Sure." right after the swap, under A's old label and 0.66 s before B's next
    # line under it: the label's pause where the swap is began at A's last line, before the
    # window B's label leaves for the change (2026-11-09 bench, en_interview_quick)
    talk = [Turn(k * 9.2 + d, 4.0, v, s) for k in range(6)
            for d, v, s in ((0.0, "A", "S1"), (4.6, "B", "S2"))]
    talk += [Turn(55.4, 0.6, "A", "S2"), Turn(56.2, 0.44, "B", "S1"), Turn(57.3, 4.0, "B", "S1")]
    talk += [Turn(61.9 + k * 9.2 + d, 4.0, v, s) for k in range(5)
             for d, v, s in ((0.0, "A", "S2"), (4.6, "B", "S1"))]
    assert one_name_each(monkeypatch, talk, "AB")
