"""Words the tolerant aligner left out (asr/unplaced.py, 2026-11-09): a copy of words placed close
by is dropped, a Gemini loop's copies too; a line no one said is spread over its own time, marked
estimated, and its stretch given back."""
from dataclasses import replace

from tarjim import guards
from tarjim.asr.unplaced import Lines, Region, all_copies, pieces, settled
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


def test_another_speaker_s_same_words_are_no_copy() -> None:
    """The review of 2026-11-09: S2 says a line S1 says just after; S2's line left out is not
    S1's copy (a listener's loop repeats one speaker's line), so it is spread, not dropped."""
    theirs = Utterance(10.0, 11.0, "S2", "water at every station", request="k0.v")
    mine = Utterance(12.0, 13.0, "S1", "water at every station", request="k0.v")
    out = settled(words_of(theirs, mine), {0, 1, 2, 3}, Lines([theirs, mine], [(0.0, 20.0)]))
    assert not out.dropped and [w.source for w in out.words[:4]] == ["estimated"] * 4


def test_a_copy_goes_whole_with_the_short_words_the_sound_still_lent_a_frame() -> None:
    """The bench, 2026-11-09 (ar_dialogue and en_refrain_twice x loop_all): the skip left out
    most of a copy but placed its "at" (or "لا", "أن") on a stray frame, so the copy came in
    two runs too short to be copies and stayed whole. A line most of which is left out is
    judged whole, and a copy is dropped with the words of it still placed."""
    copy = Utterance(13.0, 14.0, "S1", "we will meet again")
    lines = [FIRST, NEXT, copy]
    out = settled(words_of(*lines), {6, 8, 9}, Lines(lines, [(0.0, 20.0)]))
    assert out.dropped == {6, 7, 8, 9} and out.regions == []
    assert all_copies(words_of(*lines), {6, 8, 9}, Lines(lines, [(0.0, 20.0)]))


def test_a_line_s_own_words_still_placed_are_not_what_it_copies() -> None:
    line = Utterance(10.0, 12.0, "S1", "one two one two one")
    out = settled(words_of(line), {0, 1, 2}, Lines([line], [(0.0, 20.0)]))
    assert not out.dropped


def test_of_lines_written_alike_the_first_written_is_kept_with_the_times_found() -> None:
    """The bench, 2026-11-09 (en_refrain_close x loop_all): the skip placed the last copy on the
    speech and left out the line itself, so the words kept their times but came after the next
    speaker's line in the transcript, out of order. Of a speaker's lines written alike, the
    first written are kept, with the times the reading found."""
    said = Utterance(10.0, 11.0, "S1", "can I bring my dog")
    reply = Utterance(11.5, 13.0, "S2", "sorry no dogs")
    copy = Utterance(13.2, 14.2, "S1", "can I bring my dog")
    words = words_of(said, reply, copy)
    found = words_of(said)
    words[8:13] = [replace(w, speaker="S1") for w in found]
    out = settled(words, {0, 1, 2, 3, 4}, Lines([said, reply, copy], [(0.0, 20.0)]))
    assert out.dropped == {8, 9, 10, 11, 12}
    assert [(w.start, w.end) for w in out.words[:5]] == [(w.start, w.end) for w in found]
    assert {w.source for w in out.words[:5]} == {"aligned"}


def test_labels_of_another_request_do_not_tell_a_copy_apart() -> None:
    """The bench, 2026-11-09 (en_long_three_pieces x drift): a line asked again came back
    labelled "S2~x1386", its "It is still there" a copy of S3's line of the first listen.
    Labels compare only inside one request, so it is still a copy."""
    theirs = Utterance(10.0, 11.0, "S3", "it is still there", request="k2.v")
    asked = Utterance(10.0, 11.0, "S2~x1", "it is still there", request="")
    out = settled(words_of(theirs, asked), {4, 5, 6, 7}, Lines([theirs, asked], [(0.0, 20.0)]))
    assert out.dropped == {4, 5, 6, 7}


def test_words_an_earlier_reading_left_out_count_with_the_line() -> None:
    """The bench, 2026-11-09 (en_long_three_pieces x drift): one window left out "It is" of a
    line asked again, the next its "still there"; each half alone was too little of the line to
    be a copy of S3's "It is still there" beside it, so it stayed, half spread."""
    theirs = Utterance(10.0, 11.0, "S3", "it is still there", request="k2.v")
    asked = Utterance(10.0, 11.0, "S2~x1", "it is still there", request="")
    words = words_of(theirs, asked)
    words[4:6] = [replace(w, source="unplaced") for w in words[4:6]]
    assert all_copies(words, {6, 7}, Lines([theirs, asked], [(0.0, 20.0)]))


def test_a_line_whose_time_holds_only_other_lines_speech_is_not_shown() -> None:
    """The bench, 2026-11-09 (ar_dialogue x tail_hallucination): an invented "Thank you for
    watching" over the next line's speech was spread onto it, two cues at once. Speech another
    line's words were found on is not free; with too little free speech for its words the run
    is not shown, and its stretch is still given back to be asked about."""
    invented = Utterance(20.0, 21.0, "S1", "thank you for watching")
    said = Utterance(20.1, 23.0, "S1", "the children waited months")
    words = words_of(invented, said)
    out = settled(words, {0, 1, 2, 3}, Lines([invented, said], [(20.1, 23.0)]))
    assert out.unheard == {0, 1, 2, 3} and not out.dropped
    assert out.regions == [Region(20.0, 21.0, "unplaced")]


def test_a_line_with_no_speech_in_its_time_is_not_spread_on_silence() -> None:
    """The bench, 2026-11-09 (en_long_three_pieces x tail_hallucination): a line past the end
    of the speech went on silence, ten words over nothing."""
    invented = Utterance(24.3, 25.0, "S1", "do not forget to subscribe")
    out = settled(words_of(FIRST, invented), {4, 5, 6, 7, 8},
                  Lines([FIRST, invented], [(10.0, 11.0)]))
    assert out.unheard == {4, 5, 6, 7, 8} and out.estimated == 0
