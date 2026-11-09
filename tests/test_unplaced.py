"""Words the tolerant aligner left out (asr/unplaced.py, 2026-11-09): a copy of words placed close
by is dropped, a Gemini loop's copies too; a line no one said is spread over its own time, marked
estimated, and its stretch given back."""
from tarjim import guards
from tarjim.asr.unplaced import Lines, Region, pieces, settled
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

FIRST = Utterance(10.0, 11.0, "S1", "we will meet again")
NEXT = Utterance(11.2, 12.0, "S1", "next week")


def words_of(*lines: Utterance) -> list[Word]:
    """Each line's words placed one after another over its time."""
    found = []
    for u in lines:
        texts = u.text.split()
        step = (u.end - u.start) / len(texts)
        found += [Word(t, u.start + k * step, u.start + (k + 1) * step, u.speaker,
                       source="aligned") for k, t in enumerate(texts)]
    return found


def test_a_line_written_twice_drops_the_copy_left_out() -> None:
    copy = Utterance(13.0, 14.0, "S1", "we will meet again")
    lines = [FIRST, NEXT, copy]
    out = settled(words_of(*lines), {6, 7, 8, 9}, Lines(lines, [(0.0, 20.0)]))
    assert out.dropped == {6, 7, 8, 9} and out.regions == []


def test_a_loop_drops_each_copy_and_keeps_the_one_placed() -> None:
    """listen/faults loop_all: the line again twice right after itself, in every pass."""
    again = [Utterance(11.15 + k * 1.15, 12.15 + k * 1.15, "S1", FIRST.text) for k in range(2)]
    lines = [FIRST, *again]
    out = settled(words_of(*lines), set(range(4, 12)), Lines(lines, [(0.0, 20.0)]))
    assert out.dropped == set(range(4, 12))


def test_copies_further_than_near_are_not_taken_for_copies() -> None:
    far = Utterance(30.0, 31.0, "S1", "we will meet again")
    lines = [FIRST, far]
    out = settled(words_of(*lines), {4, 5, 6, 7}, Lines(lines, [(30.2, 30.8)]))
    assert out.dropped == set()
    assert [w.source for w in out.words[4:]] == ["estimated"] * 4
    assert out.words[4].start == 30.2 and abs(out.words[-1].end - 30.8) < 1e-9


def test_a_line_no_one_said_is_spread_over_its_speech_and_given_back() -> None:
    invented = Utterance(20.0, 23.0, "S2", "thank you for watching")
    lines = [FIRST, invented]
    out = settled(words_of(*lines), {4, 5, 6, 7}, Lines(lines, [(19.0, 21.0), (22.0, 22.5)]))
    spread = out.words[4:]
    assert [w.source for w in spread] == ["estimated"] * 4 and not out.dropped
    assert spread[0].start == 20.0 and abs(spread[-1].end - 22.5) < 1e-9
    assert out.regions == [Region(20.0, spread[-1].end, "unplaced")]
    assert out.words[:4] == words_of(FIRST)


def test_a_word_left_out_inside_a_line_keeps_to_its_room() -> None:
    """Only the time between the line's words placed around it, not the whole line."""
    lines = [Utterance(0.0, 4.0, "S1", "alpha bravo charlie delta")]
    words = words_of(*lines)
    out = settled(words, {2}, Lines(lines, [(0.0, 4.0)]))
    assert (out.words[2].start, out.words[2].end) == (words[1].end, words[3].start)
    assert out.words[2].source == "estimated"


def test_runs_left_out_are_split_by_their_line() -> None:
    assert pieces({1, 2, 3, 7}, [0, 0, 0, 1, 1, 1, 1, 1]) == [[1, 2], [3], [7]]


def test_each_word_is_counted_once_by_its_guard() -> None:
    guards.reset()
    copy = Utterance(13.0, 14.0, "S1", "we will meet again")
    invented = Utterance(20.0, 21.0, "S1", "zulu yankee")
    lines = [FIRST, copy, invented]
    settled(words_of(*lines), set(range(4, 10)), Lines(lines, []))
    counts = guards.counts()
    assert (counts["unplaced.duplicate"], counts["unplaced.estimated"]) == (4, 2)


def test_a_word_left_out_of_a_line_said_is_no_copy_of_the_same_word_nearby() -> None:
    """The bench, 2026-11-09: a lone "The" the skip left out of "The tomatoes did not survive."
    was dropped as a copy of the "The" of the next line."""
    said = Utterance(0.0, 2.0, "S1", "The tomatoes did not survive.")
    after = Utterance(2.5, 4.0, "S1", "The roof did, luckily.")
    out = settled(words_of(said, after), {0}, Lines([said, after], [(0.0, 4.0)]))
    assert not out.dropped and out.words[0].source == "estimated"
