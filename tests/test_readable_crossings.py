"""Two voices crossing never leave a subtitle too fast to read (2026-11-09).

Since the aligner times a turn begun over the end of another where it is said (asr/waited.py),
en_debate_overlap has real crossings, and the turn's first words were cut out as a reply on the
end of the other voice's subtitle whatever that left: "A ban is the only rule that" shown 0.94 s,
then "actually works. / You keep saying" 0.90 s, and four subtitles shown faster than 5.5 words
a second on every run. The words here are the aligner's on that clip.
"""
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.segment import build_cues
from tarjim.tracks import tracks

FASTEST = 5.5  # words a second: shown faster, a subtitle is rushed (the bench's measure)
LATE = 0.2  # seconds a subtitle may come up after its first word (fit.LATE_START)
TOLERANCE = 1e-6

Timed = list[tuple[str, float, float]]


def voice(who: str, timed: Timed) -> list[Word]:
    return [Word(text, start, end, who) for text, start, end in timed]


PUNISHES = voice("S3", [("But", 50.42, 50.54), ("a", 50.58, 50.6), ("total", 50.66, 50.96),
                        ("ban", 51.0, 51.2), ("punishes", 51.3, 51.66),
                        ("everyone.", 51.66, 51.84)])
BAN = voice("S2", [("A", 51.84, 51.86), ("ban", 51.86, 51.94), ("is", 52.0, 52.06),
                   ("the", 52.1, 52.18), ("only", 52.26, 52.44), ("rule", 52.54, 52.76),
                   ("that", 52.78, 52.88), ("actually", 52.96, 53.38), ("works.", 53.44, 53.58)])
EVIDENCE = [("that,", 53.7, 54.0), ("but", 54.32, 54.44), ("you", 54.5, 54.58),
            ("have", 54.64, 54.78), ("not", 54.82, 55.0), ("shown", 55.08, 55.3),
            ("any", 55.38, 55.52), ("evidence.", 55.64, 56.1)]
SAYING = voice("S3", [("You", 52.86, 53.18), ("keep", 53.32, 53.46), ("saying", 53.48, 53.68),
                      *EVIDENCE])
EARLIER = voice("S3", [("You", 52.42, 52.62), ("keep", 52.72, 53.06), ("saying", 53.1, 53.68),
                       *EVIDENCE])  # the same run with the listener's start 0.44 s early

SCHOOLS = voice("S2", [("Schools", 17.62, 17.96), ("have", 18.0, 18.14),
                       ("telephones.", 18.18, 18.84), ("They", 19.58, 19.68),
                       ("had", 19.72, 19.86), ("them", 19.9, 20.04), ("long", 20.1, 20.3),
                       ("before", 20.36, 20.64), ("mobile", 20.68, 21.0),
                       ("phones", 21.02, 21.3), ("existed.", 21.34, 21.52)])
STUDENTS = voice("S3", [("And", 20.4, 20.54), ("what", 20.58, 20.86), ("about", 20.88, 21.24),
                        ("students", 21.28, 21.8), ("who", 21.8, 21.86), ("use", 21.98, 22.12),
                        ("their", 22.16, 22.28), ("phones", 22.36, 22.64), ("to", 22.7, 22.76),
                        ("study,", 22.84, 23.1), ("to", 23.48, 23.56),
                        ("translate,", 23.64, 24.3), ("to", 24.56, 24.76), ("read?", 25.02, 25.22)])
COMPUTERS = voice("S2", [("They", 24.56, 24.66), ("can", 24.7, 24.84), ("use", 24.92, 25.06),
                         ("the", 25.08, 25.14), ("school", 25.2, 25.46),
                         ("computers", 25.52, 26.06), ("for", 26.1, 26.2), ("that.", 26.24, 26.48)])


def test_a_voice_heard_twice_at_once_still_gives_the_reply() -> None:
    """A line the listener gave twice over itself is too fast to read with or without the
    reply, so the reply is taken as before (en_long_three_pieces with a repeated line)."""
    once = [(f"w{k}", 10.0 + 0.3 * k, 10.25 + 0.3 * k) for k in range(8)]
    twice = voice("S1", [*once, *((t, s + 0.4, e + 0.4) for t, s, e in once)])
    turn = voice("S2", [(f"reply{k}", 12.0 + 0.4 * k, 12.3 + 0.4 * k) for k in range(12)])
    main, replies = tracks([*twice, *turn])
    assert replies == [turn[:2]] and main == [*twice, *turn[2:]]


def readable(cues: list[Cue], words: list[Word]) -> None:
    assert sorted((w for c in cues for w in c.words), key=id) == sorted(words, key=id)
    for cue in cues:
        assert cue.duration >= DEFAULT_RULES.shortest - TOLERANCE, cue
        assert len(cue.words) / cue.duration <= FASTEST, cue


def holding(cues: list[Cue], word: Word) -> Cue:
    return next(c for c in cues if any(w is word for w in c.words))


def test_a_fast_turn_said_over_keeps_its_sentence_whole() -> None:
    """Cut where the other voice began, "A ban is the only rule that" was said too fast to be
    read in the time left before it: the sentence keeps its subtitle and the other voice's
    comes up once it has been said, as before the aligner timed the crossing."""
    for said_over in (SAYING, EARLIER):
        words = [*PUNISHES, *BAN, *said_over]
        cues = build_cues(words, cuts=[])
        readable(cues, words)
        assert holding(cues, BAN[0]).words == BAN
        assert holding(cues, said_over[0]).start <= BAN[-1].end + DEFAULT_RULES.min_gap


def test_a_question_said_over_a_turn_still_shares_its_end() -> None:
    """Here the crossing can be read: the question's first words share the screen with the
    turn's last ones, and its next words come up at most LATE after they are said."""
    words = [*SCHOOLS, *STUDENTS, *COMPUTERS]
    cues = build_cues(words, cuts=[])
    readable(cues, words)
    shared = holding(cues, STUDENTS[0])
    assert shared.is_dialogue and shared.start <= STUDENTS[0].start
    assert holding(cues, SCHOOLS[-1]) is shared
    for cue in cues:
        assert cue.start <= min(w.start for w in cue.words) + LATE + TOLERANCE, cue
