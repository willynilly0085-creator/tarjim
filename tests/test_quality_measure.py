"""The bench's numbers count what the owner complained about, and nothing on good subtitles."""
from tarjim.models import Word
from tarjim.quality.measure import Shown, measured


def said(text: str, start: float, step: float = 0.4) -> list[Word]:
    return [Word(w, start + k * step, start + k * step + 0.3) for k, w in enumerate(text.split())]


FIRST = "we came here today to talk about the plan"
SECOND = "and nobody in this room wants it to fail"
WORDS = [*said(FIRST, 1.0), *said(SECOND, 6.0)]


def test_good_subtitles_measure_clean() -> None:
    shown = [Shown(1.0, 4.6, FIRST), Shown(6.0, 9.9, SECOND)]
    got = measured(shown, WORDS)
    assert (got.unshown, got.lost, got.off, got.doubled, got.rushed, got.stopped) == \
        (0.0, 0, 0, 0, 0, 0.0)
    assert got.checked == 2


def test_speech_with_no_subtitle_is_counted_and_lost_when_nowhere() -> None:
    got = measured([Shown(1.0, 4.6, FIRST)], WORDS)
    assert got.unshown > 3.0 and got.lost == len(SECOND.split())
    assert got.stopped > 1.5  # the subtitles end before the speech does


def test_a_subtitle_shown_early_is_off() -> None:
    got = measured([Shown(1.0, 4.6, FIRST), Shown(2.0, 5.9, SECOND)], WORDS)
    assert got.off == 1


def test_the_same_words_shown_twice_are_doubled() -> None:
    shown = [Shown(1.0, 4.6, FIRST), Shown(4.7, 5.9, FIRST), Shown(6.0, 9.9, SECOND)]
    assert measured(shown, WORDS).doubled == 1


def test_words_said_twice_shown_twice_are_not_doubled() -> None:
    chant = said(f"{FIRST} {FIRST}", 1.0)
    shown = [Shown(1.0, 4.6, FIRST), Shown(5.0, 8.6, FIRST)]
    assert measured(shown, chant).doubled == 0


def test_words_piled_on_an_instant_are_rushed() -> None:
    assert measured([Shown(1.0, 1.4, FIRST)], []).rushed == 1


def test_nothing_to_measure_against_counts_only_what_needs_no_yardstick() -> None:
    got = measured([Shown(1.0, 4.6, FIRST)], [])
    assert (got.words, got.unshown, got.off, got.stopped) == (0, 0.0, 0, 0.0)
