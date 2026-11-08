"""Each word says how it got its time (2026-11-08): the aligner heard its letters (with their
score), the local listener heard it, it was spread by its length, or it was placed between the
words around it."""
from typing import Any

import pytest

from tarjim.asr import align, vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.fuse import fuse
from tarjim.asr.piles import spread
from tarjim.asr.qwen import attach_punctuation
from tarjim.asr.spread import proportional
from tarjim.engines.local_listen import utterances_from
from tarjim.listen.coverage import Gap
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.repair import from_words
from tarjim.models import Word
from tests.test_emissions_once import SECONDS, Emitter, Hearing, Roman, clip


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> AlignEngine:
    made = AlignEngine.__new__(AlignEngine)
    made.emitter, made.roman = Emitter(Hearing()), Roman()  # type: ignore[assignment]
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    monkeypatch.setattr(align, "shared_aligner", lambda: made)
    return made


def sources(words: list[Word]) -> list[str]:
    return [w.source for w in words]


def test_the_aligner_says_which_words_it_heard(engine: AlignEngine) -> None:
    lines = [Utterance(2.5, 4.5, "S1", "alpha ~~"), Utterance(24.5, 26.5, "S1", "bravo")]
    words = engine.align(clip(), lines, "English")
    assert sources(words) == ["aligned", "unplaced", "aligned"]
    assert words[0].score is not None and words[1].score is None


def test_a_line_the_aligner_cannot_follow_is_estimated(engine: AlignEngine) -> None:
    words = engine.align(clip(), [Utterance(10.0, 12.0, "S1", "!!! ???")], "English")
    assert sources(words) == ["estimated", "estimated"]


def test_spread_and_piled_words_are_estimated() -> None:
    assert set(sources(proportional(Utterance(1.0, 2.0, "S1", "one two")))) == {"estimated"}
    pile = [Word("a", 5.0, 5.01, source="aligned"), Word("b", 5.0, 5.02, source="aligned")]
    assert sources(spread(pile, (4.0, 6.0), [])) == ["estimated", "estimated"]


def test_fused_words_are_heard_or_placed_between_them() -> None:
    lines = [Utterance(15.0, 17.0, "S1", "one two three")]
    aligned = [Word("one", 20.0, 20.1, "S1", source="aligned"),
               Word("two", 20.1, 20.2, "S1", source="aligned"),
               Word("three", 20.2, 20.3, "S1", source="aligned")]
    heard = [Word("one", 15.1, 15.4, source="heard"), Word("three", 16.0, 16.4, source="heard")]
    fused = fuse(aligned, lines, heard)
    assert sources(fused) == ["heard", "unplaced", "heard"]


def test_the_local_listeners_words_and_lines_say_so() -> None:
    timed: list[Any] = [type("Stamp", (), {"text": "hello", "start_time": 1.0, "end_time": 1.4})]
    [word] = attach_punctuation("hello", timed)
    assert word.source == "heard"
    lines = utterances_from([word, Word("again", 3.0, 3.3, source="heard")])
    assert [u.request for u in lines] == ["local", "local"]
    assert lines[0].piece == (0.0, 3.3)
    assert [u.request for u in from_words([word])] == ["local"]


def test_lines_the_local_words_fill_carry_the_sound_asked_about() -> None:
    from tarjim.listen.asked import heard_span
    from tarjim.listen.coverage import Hearing
    from tarjim.listen.repair import Mender

    words = [Word("filled", 30.0, 30.5, source="heard"), Word("in", 30.6, 30.8, source="heard")]
    gap = Gap(29.0, 32.0, 0.8, words)
    hearing = Hearing([], words, [(0.0, 60.0)])
    [line] = Mender(hearing, None, "").from_local(gap, [])
    assert line.piece == heard_span(29.0, 32.0) and line.request == "local"
