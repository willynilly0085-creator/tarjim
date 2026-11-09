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
from tarjim.listen.chunks import SLIPPED
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


def test_a_slipped_line_is_not_searched_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09: a line read back from an mm:ss misread outside its piece (listen/chunks
    SLIPPED) has no time to trust; searched alone inside another line, it takes that line's
    letters. It is not searched again."""
    after = {"kilo": 5.6, "lima": 6.0, "mike": 6.4, "oscar": 6.8, "papa": 7.3}
    said = {"alpha": 0.5, "bravo": 1.5, "whiskey": 4.9, **after}
    line = Utterance(2.4, 5.2, "S2", "kilo lima mike oscar papa", prior=SLIPPED)
    times = aligned(line, monkeypatch, said)
    assert all(abs(times[word] - at) < 0.1 for word, at in after.items())  # not on "whiskey"
    assert guards.counts()["align.unwaited"] == 0


def test_an_overlap_with_wrong_words_still_moves(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09, en_debate_overlap wrong_words: with the listener's words partly wrong, half of
    the host's line and under half of the turn said over its end are found, and a rule asking for
    more than half kept the turn waiting: the gain over the earlier search was lost. A third
    found is enough to be said there."""
    host = Utterance(0.0, 5.4, "S1", "alpha cog fizz whiskey")  # 2 of 4 found
    turn = Utterance(4.7, 7.5, "S2", "ox gum fqz india juliet")  # 2 of 5 found in the one search
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(SAID), Roman()  # type: ignore[assignment]
    words = engine.align(np.zeros(16), [host, turn], "English")
    assert words[4].text == "ox" and abs(words[4].start - 4.7) < 0.1
    assert guards.counts()["align.unwaited"] == 1


def found_at(letters: str, start: float, speaker: str, scores: list[float]) -> list[Word]:
    return [Word(t, start + k * 0.4, start + k * 0.4 + 0.3, speaker, score=s)
            for k, (t, s) in enumerate(zip(letters, scores, strict=True))]


HEARD_LINES = [Utterance(0.0, 5.4, "S1", "a b w"), Utterance(5.0, 8.0, "S2", "k l m n o")]
QUESTION = found_at("abw", 0.5, "S1", [0.98] * 3)


def test_a_line_the_one_search_did_not_find_is_not_searched_again() -> None:
    """2026-11-09, en_long_three_pieces and en_monologue slip: a line the listener put a minute
    late, inside its piece, landed in another line, where its words are not said: the one search
    found 1 or 2 of its 10 or 11 words. Searched alone, it took the other line's letters and cut
    its subtitle short (en_monologue: 14 words missed instead of 1). A turn said over another's
    end goes on after it, where the one search finds its later words (6 of 14 or more)."""
    unsaid = found_at("klmno", 6.0, "S2", [0.9, 0.01, 0.01, 0.01, 0.01])  # 1 of 5
    assert waited(HEARD_LINES, [False] * 2, [*QUESTION, *unsaid]) == []
    goes_on = found_at("klmno", 6.0, "S2", [0.01, 0.01, 0.01, 0.9, 0.9])  # 2 of 5
    assert waited(HEARD_LINES, [False] * 2, [*QUESTION, *goes_on]) == [(1, 3)]


def test_a_turn_does_not_wait_for_a_line_not_found_where_it_is() -> None:
    """2026-11-09, mixed_en_ar slip: the guest's answer was said over a line the listener put a
    minute late, whose words the one search did not find there (1 of 11). Moved under it, the
    answer shared a subtitle with that line and showed its first words late: 3 words missed
    instead of 1. A line found there, if only one word in three, does make a turn wait."""
    lines = [Utterance(0.0, 5.4, "S1", "a b w"), Utterance(5.0, 7.5, "S1", "y z x"),
             Utterance(5.6, 9.0, "S2", "o i j")]
    answer = found_at("oij", 7.6, "S2", [0.98] * 3)
    unsaid = found_at("yzx", 6.0, "S1", [0.001] * 3)
    assert waited(lines, [False] * 3, [*QUESTION, *unsaid, *answer]) == []
    partly = found_at("yzx", 6.0, "S1", [0.001, 0.98, 0.001])
    assert waited(lines, [False] * 3, [*QUESTION, *partly, *answer]) == [(2, 6)]
    lines[1] = replace(lines[1], prior=SLIPPED)  # read back from an mm:ss misread: no part
    assert waited(lines, [False] * 3, [*QUESTION, *partly, *answer]) == []
