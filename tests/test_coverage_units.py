"""What counts as speech left out, and how a stretch heard again joins the lines already there."""
import pytest

from tarjim.listen.coverage import Hearing, gap_seconds, gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.repair import from_words, mend
from tarjim.models import Word

LINE = Utterance(0.0, 10.0, "S1", "one two three four five")


def test_a_breath_or_a_short_word_is_not_a_gap() -> None:
    hearing = Hearing([LINE], [], [(0.0, 10.0), (10.4, 11.5), (30.0, 31.0)])
    assert gaps(hearing) == []


def test_pieces_of_speech_with_short_pauses_join_into_one_gap() -> None:
    hearing = Hearing([LINE], [], [(0.0, 10.0), (20.0, 21.2), (21.8, 23.0)])
    [gap] = gaps(hearing)
    assert (gap.start, gap.end, round(gap.speech, 1)) == (20.0, 23.0, 2.4)


def test_local_words_alone_show_a_gap_when_the_voice_detector_is_missing() -> None:
    words = [Word(f"w{k}", 20.0 + k * 0.5, 20.4 + k * 0.5) for k in range(8)]
    [gap] = gaps(Hearing([LINE], words, []))
    assert len(gap.words) == 8 and gap.start == 20.0


def test_nothing_to_check_against_finds_nothing() -> None:
    assert gaps(Hearing([LINE], [], [])) == []


def test_the_shortest_gap_is_a_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    hearing = Hearing([LINE], [], [(20.0, 21.5)])
    assert gaps(hearing) == []
    monkeypatch.setenv("TARJIM_COVERAGE_GAP_SECONDS", "1")
    assert gap_seconds() == 1.0 and len(gaps(hearing)) == 1


def test_lines_heard_again_that_repeat_the_edge_are_dropped(
        capsys: pytest.CaptureFixture[str]) -> None:
    hearing = Hearing([LINE], [], [(0.0, 10.0), (12.0, 20.0)])

    def again(_start: float, _end: float) -> list[Utterance]:
        return [Utterance(9.0, 10.5, "S1", "four five"),  # the end of the line before
                Utterance(8.5, 12.5, "S2", "one two three four five"),
                Utterance(12.0, 20.0, "S1", "six seven eight")]

    mended = mend(hearing, again, "somecloud")
    assert [u.text for u in mended.added] == ["six seven eight"]
    assert [u.text for u in mended.utterances] == [LINE.text, "six seven eight"]
    assert "re-listened with somecloud: 1 lines" in capsys.readouterr().out


def test_speech_no_listener_heard_words_in_does_not_hold_the_hearing_back(
        capsys: pytest.CaptureFixture[str]) -> None:
    local = [Word("one", 0.5, 1.0)]
    mended = mend(Hearing([LINE], local, [(0.0, 10.0), (40.0, 45.0)]), lambda _a, _b: [], "x")
    assert mended.whole and mended.added == []
    assert "no listener heard words here" in capsys.readouterr().out


def test_without_an_engine_to_ask_and_no_words_the_gap_is_left() -> None:
    mended = mend(Hearing([LINE], [], [(40.0, 45.0)]), None, "")
    assert not mended.whole and mended.left[0].start == 40.0


def test_local_words_become_lines_at_pauses() -> None:
    words = [Word("a", 0.0, 0.3), Word("b", 0.4, 0.7), Word("c", 2.0, 2.3)]
    assert [(u.start, u.text) for u in from_words(words)] == [(0.0, "a b"), (2.0, "c")]
