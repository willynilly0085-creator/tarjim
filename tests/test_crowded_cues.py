"""A short reply between two turns, and a turn said over the end of another, never make the
next speech's subtitle wait past its first words (2026-11-08). Before, "Right." was held for
rules.shortest and the answer after it came up 0.56 s after it began, and a speaker who talked
over the end of a turn was shown only once that turn's subtitle had gone."""
from itertools import pairwise

from tarjim.models import Cue, Word
from tarjim.reading import read_time
from tarjim.rules import DEFAULT_RULES
from tarjim.segment import build_cues

RULES = DEFAULT_RULES
LATE = 0.2  # seconds a subtitle may come up after its first word
TOLERANCE = 1e-6


def timed(text: str, times: list[tuple[float, float]], who: str) -> list[Word]:
    return [Word(token, *span, who) for token, span in zip(text.split(), times, strict=True)]


# en_interview_quick at 24.8 to 31.6 s, as the aligner timed it
WARN = timed("They also use them to find food and to warn each other about danger.",
             [(24.78, 24.92), (25.0, 25.24), (25.4, 25.54), (25.58, 25.72), (25.78, 25.84),
              (25.92, 26.18), (26.28, 26.5), (26.58, 26.68), (26.72, 26.78), (26.88, 27.1),
              (27.2, 27.34), (27.38, 27.56), (27.6, 27.88), (27.92, 28.32)], "S2")
RIGHT = timed("Right.", [(28.62, 28.88)], "S1")
LOUDER = timed("The problem is that the ocean is getting much louder.",
               [(29.04, 29.14), (29.18, 29.56), (29.64, 29.76), (29.82, 29.96), (29.98, 30.08),
                (30.18, 30.44), (30.5, 30.6), (30.66, 30.92), (30.96, 31.16), (31.24, 31.56)],
               "S2")


def holding(cues: list[Cue], word: Word) -> Cue:
    return next(c for c in cues if any(w is word for w in c.words))


def kept_promises(cues: list[Cue], words: list[Word]) -> None:
    assert sorted((w for c in cues for w in c.words), key=id) == sorted(words, key=id)
    for cue in cues:
        assert cue.duration >= RULES.shortest - TOLERANCE, cue
        assert cue.start <= min(w.start for w in cue.words) + LATE + TOLERANCE, cue
    for first, second in pairwise(cues):
        assert first.end + RULES.min_gap <= second.start + TOLERANCE, (first, second)


def test_a_one_word_reply_shares_the_screen_with_the_answer_instead_of_delaying_it() -> None:
    words = [*WARN, *RIGHT, *LOUDER]
    cues = build_cues(words, cuts=[])
    kept_promises(cues, words)
    shown = holding(cues, RIGHT[0])
    assert shown.is_dialogue and shown.parts[0] == RIGHT
    assert shown.parts[1] == LOUDER[:len(shown.parts[1])]
    assert all(len(" ".join(w.text for w in p)) <= RULES.part_chars for p in shown.parts)


ANYMORE = "So the whales cannot hear each other across the ocean anymore."


def test_a_reply_that_fits_a_short_wait_keeps_the_answer_whole() -> None:
    """A wait of up to 0.2 s is taken before any sentence is cut in two."""
    reply = timed("Right.", [(28.42, 28.6)], "S1")
    answer = timed(ANYMORE, [(29.3 + 0.3 * k, 29.5 + 0.3 * k) for k in range(11)], "S2")
    words = [*WARN, *reply, *answer]
    cues = build_cues(words, cuts=[])
    kept_promises(cues, words)
    assert [c.source for c in cues[-2:]] == ["Right.", ANYMORE]
    assert cues[-1].start > answer[0].start


# en_debate_overlap at 7.5 to 13.9 s: the second voice starts 0.6 s before the first one stops
FOCUS = timed("Children cannot focus when a phone is buzzing in their pocket.",
              [(7.58, 8.05), (8.05, 8.4), (8.4, 8.79), (8.8, 8.95), (8.95, 9.0), (9.0, 9.28),
               (9.28, 9.4), (9.4, 9.74), (9.74, 9.85), (9.85, 9.99), (9.99, 10.35)], "S2")
SIMPLE = timed("That is far too simple.",
               [(9.75, 9.92), (9.92, 10.07), (10.07, 10.31), (10.31, 10.56), (10.56, 11.03)],
               "S3")
COMMON = timed("It is not simple, it is common sense.",
               [(11.78, 11.9), (11.9, 12.02), (12.02, 12.21), (12.21, 12.6), (12.86, 12.98),
                (12.98, 13.1), (13.12, 13.44), (13.44, 13.94)], "S2")


def on_screen(cues: list[Cue], word: Word) -> bool:
    """Up from the word's start to its middle, 0.3 s either way, as the bench counts it."""
    shown, slack = holding(cues, word), 0.3
    return shown.start - slack <= word.start and (word.start + word.end) / 2 <= shown.end + slack


def test_a_turn_said_over_the_end_of_another_shares_its_subtitle() -> None:
    words = [*FOCUS, *SIMPLE, *COMMON]
    cues = build_cues(words, cuts=[])
    kept_promises(cues, words)
    assert all(on_screen(cues, w) for w in words)
    shown = holding(cues, SIMPLE[0])
    assert shown.is_dialogue and shown.parts[1] == SIMPLE
    assert shown.parts[0] == FOCUS[-3:]  # "in their pocket.", said while the reply starts


# en_debate_overlap at 19.5 to 26.5 s: a long question said over the end of a turn, and the
# answer to it starting 0.5 s before the question ends
EXISTED = timed("They had them long before mobile phones existed.",
                [(19.58, 19.7), (19.7, 19.91), (19.91, 20.07), (20.07, 20.34), (20.34, 20.65),
                 (20.65, 20.98), (20.98, 21.32), (21.32, 21.84)], "S2")
STUDY = timed("And what about students who use their phones to study, to translate, to read?",
              [(20.64, 20.79), (20.79, 20.98), (20.98, 21.23), (21.27, 21.74), (21.74, 21.88),
               (21.88, 22.13), (22.17, 22.3), (22.3, 22.67), (22.7, 22.79), (22.79, 23.23),
               (23.48, 23.61), (23.61, 24.33), (24.6, 24.74), (24.74, 25.06)], "S3")
SCHOOL = timed("They can use the school computers for that.",
               [(24.56, 24.68), (24.68, 24.85), (24.85, 25.06), (25.06, 25.15), (25.15, 25.5),
                (25.5, 26.08), (26.08, 26.22), (26.22, 26.46)], "S2")


def test_a_long_turn_said_over_another_waits_for_it_to_be_read() -> None:
    """Sharing the screen, the turn's end and the question's first words would be shown 1.44 s
    at most, 5.6 words a second (2026-11-09): the turn keeps its subtitle whole and the question
    comes up once it has been read, before its words end. On the aligner's own times the two
    can be read sharing the screen, and do (test_readable_crossings)."""
    words = [*EXISTED, *STUDY, *SCHOOL]
    cues = build_cues(words, cuts=[])
    assert [c.words for c in cues] == [EXISTED, STUDY, SCHOOL]
    for first, second in pairwise(cues):
        assert first.end + RULES.min_gap <= second.start + TOLERANCE, (first, second)
    question = holding(cues, STUDY[0])
    assert EXISTED[0].start + read_time(EXISTED) <= question.start <= EXISTED[-1].end
    assert all(c.duration >= read_time(c.words) - TOLERANCE for c in cues)
    assert holding(cues, SCHOOL[0]).start == SCHOOL[0].start


def test_a_short_overlap_does_not_make_the_answer_come_up_late() -> None:
    """The answer starts 0.5 s before the question ends. Bringing it up 0.2 s late only moved
    0.2 s of what is not shown from the question's end to the answer's start (2026-11-08)."""
    words = [*STUDY, *SCHOOL]
    cues = build_cues(words, cuts=[])
    kept_promises(cues, words)
    assert [c.source for c in cues] == [" ".join(w.text for w in STUDY),
                                        " ".join(w.text for w in SCHOOL)]
    assert cues[1].start == SCHOOL[0].start


# unlabelled words where every one of them fits one subtitle: a late start for "Cannot" left
# just enough room for "Wow. ... Yes." alone, and the join that showed every word was not made
CROSSED = [Word("problems", 5.918, 6.401), Word("is", 6.547, 6.876), Word("they?", 6.877, 7.259),
           Word("Wow.", 7.479, 7.967), Word("Other", 7.489, 7.845),
           Word("other", 7.867, 8.199), Word("rare.", 8.241, 8.737), Word("Yes.", 8.251, 8.706),
           Word("Cannot", 8.295, 8.482), Word("they", 8.612, 8.924),
           Word("getting", 8.998, 9.307), Word("it", 9.319, 9.695), Word("is?", 9.798, 10.182)]


def test_crossed_turns_that_fit_one_subtitle_are_joined_into_it() -> None:
    cues = build_cues(list(CROSSED), cuts=[])
    kept_promises(cues, CROSSED)
    assert [c.source for c in cues] == ["problems is they?", " ".join(w.text for w in CROSSED[3:])]
    assert all(on_screen(cues, w) for w in CROSSED)


def test_unlabelled_turns_keep_their_old_order() -> None:
    words = [Word(w.text, w.start, w.end) for w in [*FOCUS, *SIMPLE, *COMMON]]
    cues = build_cues(words, cuts=[])
    assert all(len(c.parts) <= 2 for c in cues)
    for first, second in pairwise(cues):
        assert first.end + RULES.min_gap <= second.start + TOLERANCE
