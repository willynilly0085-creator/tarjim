"""What is left of a broken pass, and phrases said twice, in the vote (2026-11-08)."""
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import agreed
from tarjim.listen.recover import best_heard
from tarjim.listen.vote import vote

U = Utterance
GOOD = [U(k * 4.0, k * 4.0 + 3.5, "S1", f"line {k} has five words") for k in range(30)]
GIANT = U(0.0, 129.0, "S1", " ".join(u.text for u in GOOD))


def test_a_pass_left_with_a_line_or_two_does_not_outvote_the_good_pass() -> None:
    broken = [GIANT, GOOD[0]]  # all of its speech in one impossible line, and one real line
    voted = agreed([GOOD, broken])
    assert len(voted) == len(GOOD)
    assert len(best_heard(voted, [GOOD, broken], [])) == len(GOOD)


CHANT = "allahu akbar"
TAIL = U(10.0, 14.0, "S1", "and then the whole crowd went quiet for a while")


def test_a_chant_said_twice_back_to_back_stays_twice() -> None:
    base = [U(0.0, 2.0, "S1", CHANT), TAIL]
    twice = [U(0.0, 2.0, "S1", CHANT), U(2.5, 4.5, "S1", CHANT),
             U(10.0, 14.0, "S1", "and then the whole crowd went quiet")]
    starts = [u.start for u in vote([base, twice, twice]) if u.text == CHANT]
    assert len(starts) == 2 and starts[0] < 1.0 and starts[1] > 2.0
