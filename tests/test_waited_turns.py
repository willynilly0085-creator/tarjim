"""A long turn begun over the end of another is timed where it was said, not after the other
one's last letters (2026-11-08). The one in-order search made "That is far too simple." wait for
the end of the turn it was said over: 0.55 s late on every en_debate_overlap run."""
from dataclasses import replace
from typing import Any

import numpy as np
import pytest

from tarjim import guards
from tarjim.asr import vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.asr.waited import waited
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

LETTERS = "abcdefghijklmnopqrstuvwxyz"
SECONDS = 12.0
HOST = Utterance(0.0, 5.4, "S1", "alpha bravo whiskey")
SAID = {"alpha": 0.5, "bravo": 1.5, "ox": 4.7, "whiskey": 4.9, "india": 6.0, "juliet": 7.0}


class Emitter:
    vocab = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3} | {
        ch: 4 + k for k, ch in enumerate(LETTERS)}

    def __init__(self, said: dict[str, float]) -> None:
        frames, size = int(SECONDS / FRAME), len(self.vocab)
        probs = np.full((frames, size), 0.02 / size)
        probs[:, 0] = 0.98
        for word, at in said.items():
            for k, ch in enumerate(word):
                first = int(at / FRAME) + 3 * k
                probs[first:first + 3] = 0.02 / size
                probs[first:first + 3, self.vocab[ch]] = 0.98
        self.logp = np.log(probs)

    def emissions(self, _wav: Any) -> np.ndarray:
        return self.logp


class Roman:
    def romanize_string(self, text: str) -> str:
        return text


@pytest.fixture(autouse=True)
def fresh() -> None:
    guards.reset()


def aligned(turn: Utterance, monkeypatch: pytest.MonkeyPatch,
            said: dict[str, float] = SAID) -> dict[str, float]:
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(said), Roman()  # type: ignore[assignment]
    words = engine.align(np.zeros(16), [HOST, turn], "English")
    assert [w.text for w in words] == [*HOST.text.split(), *turn.text.split()]
    return {w.text: w.start for w in words}


def test_a_turn_begun_over_the_end_of_another_starts_where_it_was_said(
        monkeypatch: pytest.MonkeyPatch) -> None:
    times = aligned(Utterance(4.7, 7.5, "S2", "ox india juliet"), monkeypatch)
    assert abs(times["ox"] - 4.7) < 0.1
    assert abs(times["whiskey"] - 4.9) < 0.1 and abs(times["india"] - 6.0) < 0.1
    assert guards.counts()["align.unwaited"] == 1


def test_a_turn_timed_close_to_its_own_start_is_not_searched_again(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Said 0.3 s before the listener's start, where its own letters are: the search kept it."""
    times = aligned(Utterance(5.3, 7.5, "S2", "ox india juliet"), monkeypatch)
    assert abs(times["whiskey"] - 4.9) < 0.1 and abs(times["india"] - 6.0) < 0.1
    assert guards.counts()["align.unwaited"] == 0


def test_a_turn_whose_words_are_not_heard_where_it_was_put_keeps_its_place(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09, en_monologue slip: a line put a minute late landed inside another line, where
    its words are not said. Searched alone, it took the other line's letters (4 of its 10 words
    found there), and that line's subtitle was cut short under it: 14 words missed instead of 1.
    Searched alone, a turn moves only when most of its words are found where it lands."""
    after = {"kilo": 5.6, "lima": 6.0, "mike": 6.4, "oscar": 6.8, "papa": 7.3}
    said = {"alpha": 0.5, "bravo": 1.5, "whiskey": 4.9, **after}
    times = aligned(Utterance(2.4, 5.2, "S2", "kilo lima mike oscar papa"), monkeypatch, said)
    assert all(abs(times[word] - at) < 0.1 for word, at in after.items())  # not on "whiskey"
    assert guards.counts()["align.unwaited"] == 0


def test_a_voice_does_not_wait_for_its_own_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09, en_long_seven slip: a line the listener put a minute late, in the same voice's
    question, was searched alone and took letters over that question (6 of its 11 words found
    there), shown rushed across two subtitles. One voice does not speak over its own line: a
    turn begun inside its own speaker's line is not searched again."""
    times = aligned(Utterance(4.7, 7.5, "S1", "ox india juliet"), monkeypatch)
    assert times["ox"] >= times["whiskey"]
    assert guards.counts()["align.unwaited"] == 0


def test_a_turn_does_not_wait_for_a_line_not_heard_where_it_is() -> None:
    """2026-11-09, mixed_en_ar slip: the guest's answer was said over a line the listener put a
    minute late, whose words are not said there (1 of its 11 found). Moved under it, the answer
    shared a subtitle with that line and showed its first words late: 3 words missed instead of
    1. Only the letters of a line heard where it is make a turn wait."""
    lines = [Utterance(0.0, 5.4, "S1", "alpha bravo whiskey"),
             Utterance(5.0, 7.5, "S2", "yankee zulu xray"),
             Utterance(5.6, 9.0, "S1", "ox india juliet")]
    host = [Word(t, k * 1.5, k * 1.5 + 0.4, "S1", score=0.98) for k, t in enumerate("abw")]
    said = [Word(t, 6.0 + k * 0.4, 6.3 + k * 0.4, "S2", score=0.98) for k, t in enumerate("yzx")]
    unsaid = [replace(w, start=w.start - 1.0, end=w.end - 1.0, score=0.001) for w in said]
    answer = [Word(t, 7.6 + k, 7.9 + k, "S1", score=0.98) for k, t in enumerate("oij")]
    assert waited(lines, [False] * 3, [*host, *said, *answer]) == [(1, 3), (2, 6)]
    assert waited(lines, [False] * 3, [*host, *unsaid, *answer]) == []
