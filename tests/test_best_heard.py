"""When the passes disagree, the hearing the audio backs most is kept (2026-10-31: two passes
stopped before Obama spoke, the vote dropped his whole speech)."""
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.recover import best_heard
from tarjim.models import Word

INTRO = "please welcome to the stage the president of the united states"
SPEECH = "hello atlanta it is good to be back in georgia it is great to be with you"


def said(text: str, start: float) -> list[Word]:
    return [Word(w, start + k * 0.4, start + k * 0.4 + 0.3) for k, w in enumerate(text.split())]


def test_a_pass_that_heard_the_speech_wins_over_a_vote_that_dropped_it() -> None:
    full = [Utterance(30.0, 40.0, "S1", INTRO), Utterance(92.0, 110.0, "S2", SPEECH)]
    short = [Utterance(30.0, 40.0, "S1", INTRO)]
    heard = said(INTRO, 30.0) + said(SPEECH, 92.0)
    assert best_heard(short, [full, short, short], heard) == full


def test_a_pass_with_made_up_lines_does_not_win() -> None:
    real = [Utterance(30.0, 40.0, "S1", INTRO)]
    invented = [*real, Utterance(50.0, 60.0, "S1", "thank you all so much for coming tonight")]
    assert best_heard(real, [invented, real], said(INTRO, 30.0)) == real


def test_without_the_local_words_the_vote_stands() -> None:
    voted = [Utterance(0.0, 2.0, "S1", "hello there")]
    assert best_heard(voted, [[Utterance(0.0, 9.0, "S1", SPEECH)]], []) == voted
