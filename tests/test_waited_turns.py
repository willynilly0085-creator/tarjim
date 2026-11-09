"""A long turn begun over the end of another is timed where it was said, not after the other
one's last letters (2026-11-08). The one in-order search made "That is far too simple." wait for
the end of the turn it was said over: 0.55 s late on every en_debate_overlap run."""
from typing import Any

import numpy as np
import pytest

from tarjim import guards
from tarjim.asr import vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.listen.gemini_listen import Utterance

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


def aligned(turn: Utterance, monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(SAID), Roman()  # type: ignore[assignment]
    words = engine.align(np.zeros(16), [HOST, turn], "English")
    assert [w.text for w in words] == ["alpha", "bravo", "whiskey", "ox", "india", "juliet"]
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


def emitter(said: list[tuple[str, float]]) -> Emitter:
    """The letters of each word at its time; a word may be said more than once."""
    found = Emitter({})
    size = len(found.vocab)
    probs = np.exp(found.logp)
    for word, at in said:
        for k, ch in enumerate(word):
            first = int(at / FRAME) + 3 * k
            probs[first:first + 3] = 0.02 / size
            probs[first:first + 3, found.vocab[ch]] = 0.98
    found.logp = np.log(probs)
    return found


def test_a_turn_is_not_moved_onto_the_same_words_said_by_the_other_voice(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09: a reply "Thank you." the listener put over the host's "Thank you so much for
    joining us." was searched in its own time and took the host's "Thank you", 2 s before it was
    said, and its subtitle ended 0.6 s before the speech did."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    said = [("alpha", 0.5), ("bravo", 1.0), ("whiskey", 1.5), ("alpha", 3.0), ("bravo", 3.5)]
    engine.emitter, engine.roman = emitter(said), Roman()  # type: ignore[assignment]
    host = Utterance(0.3, 2.0, "S1", "alpha bravo whiskey")
    reply = Utterance(1.1, 2.5, "S2", "alpha bravo")
    words = engine.align(np.zeros(16), [host, reply], "English")
    assert [round(w.start, 1) for w in words][3:] == [3.0, 3.5]
    assert guards.counts()["align.unwaited"] == 0
