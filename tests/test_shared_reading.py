"""Two subtitles too full to be read either way share the time between them (2026-11-09).

On mixed_en_ar with the listener's line given three times, a copy said at 6.7 words a second
ran into the answer said over its end: it was shown 0.90 s with eleven words, and the answer
after it waited for nothing. Now the answer comes up when both would be shown at one pace, and
the line after the answer waits for it to be read.
The words are the aligner's on that clip.
"""
from tarjim.models import Cue, Word
from tarjim.reading import read_time
from tarjim.segment import build_cues

TOLERANCE = 0.1  # the gap between them, and a word's rounding


LINE = "You restore old houses in the historic part of the city."
REPLY = "نعم، أعمل في ترميم البيوت القديمة منذ خمس عشرة سنة."


def voice(who: str, text: str, timed: list[tuple[float, float]]) -> list[Word]:
    return [Word(token, *span, who) for token, span in zip(text.split(), timed, strict=True)]


FIRST = voice("S1", LINE, [(14.54, 14.62), (14.68, 15.06), (15.14, 15.28), (15.34, 15.74),
                           (15.82, 15.88), (15.9, 15.98), (16.02, 16.52), (16.58, 16.82),
                           (16.84, 16.92), (16.94, 17.02), (17.08, 17.32)])
COPY = voice("S1", LINE, [(17.48, 17.58), (17.58, 17.82), (17.84, 18.0), (18.0, 18.14),
                          (18.16, 18.2), (18.2, 18.28), (18.28, 18.66), (18.66, 18.76),
                          (18.8, 18.84), (18.84, 18.92), (19.0, 19.12)])
ANSWER = voice("S2", REPLY, [(18.18, 18.58), (19.2, 19.56), (19.68, 19.78), (19.86, 20.26),
                             (20.3, 20.72), (20.78, 21.28), (21.54, 21.74), (21.88, 22.18),
                             (22.4, 22.8), (23.1, 23.32)])
AGAIN = voice("S1", LINE, [(20.24, 20.36), (20.38, 20.78), (20.78, 21.06), (21.1, 21.56),
                           (21.58, 21.68), (21.7, 21.78), (21.9, 22.6), (22.6, 22.88),
                           (23.0, 23.06), (23.1, 23.18), (23.26, 23.46)])


def holding(cues: list[Cue], word: Word) -> Cue:
    return next(c for c in cues if any(w is word for w in c.words))


def test_two_subtitles_too_full_to_read_are_shown_at_one_pace() -> None:
    cues = build_cues([*FIRST, *COPY, *ANSWER, *AGAIN], cuts=[])
    copy, answer = holding(cues, COPY[-1]), holding(cues, ANSWER[-1])
    assert copy is not answer and copy.words == COPY
    assert copy.duration > 1.2  # 8.3 words a second: as fast as the answer, given the time
    assert answer.duration >= read_time(answer.words)  # which the line after it waits for
    assert answer.start <= COPY[-1].end + TOLERANCE  # never after the copy has been said
