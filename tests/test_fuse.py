from tarjim.asr.fuse import fuse
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

SENTENCES = [Utterance(15.0, 17.0, "S4", "Once a month."),
             Utterance(17.0, 18.0, "S1", "Nice."),
             Utterance(18.0, 21.5, "S5", "Oh my gosh.")]
ALIGNED = [Word("Once", 16.68, 16.84, "S4"), Word("a", 16.84, 16.86, "S4"),
           Word("month.", 16.9, 17.16, "S4"), Word("Nice.", 18.92, 19.0, "S1"),
           Word("Oh", 19.0, 19.08, "S5"), Word("my", 19.12, 19.22, "S5"),
           Word("gosh.", 19.26, 19.88, "S5")]
HEARD = [Word("Once", 13.2, 13.44), Word("a", 14.56, 15.68), Word("month.", 16.8, 17.2),
         Word("Nice.", 17.92, 18.24), Word("Oh", 18.96, 19.04)]


def test_sentence_outside_its_time_takes_the_second_opinion() -> None:
    fused = fuse(ALIGNED, SENTENCES, HEARD)
    nice = next(w for w in fused if w.text == "Nice.")
    assert (nice.start, nice.end) == (17.92, 18.24)


def test_sentence_inside_its_time_keeps_the_aligner() -> None:
    fused = fuse(ALIGNED, SENTENCES, HEARD)
    assert fused[0].start == 16.68
    assert [w.text for w in fused] == [w.text for w in ALIGNED]


def test_second_opinion_that_would_overlap_a_neighbour_is_ignored() -> None:
    crowded = [Word("Nice.", 17.0, 19.3)]
    fused = fuse(ALIGNED, SENTENCES, crowded)
    assert next(w for w in fused if w.text == "Nice.").start == 18.92
