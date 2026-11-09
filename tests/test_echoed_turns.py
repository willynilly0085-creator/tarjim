"""A waited turn's own search is not kept when it takes another turn's same words, unless the
two voices said them at once (asr/echoed.py, 2026-11-09). Moved here from test_waited_turns.py
on 2026-11-09, when the loop guard's tests joined that file."""
import numpy as np
import pytest

from tarjim import guards
from tarjim.asr import vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.listen.gemini_listen import Utterance
from tests.test_waited_turns import SECONDS, Emitter, Roman, fresh  # noqa: F401


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
    assert guards.counts()["align.unwaited"] == 0 and guards.counts()["align.echoed"] == 1


def test_a_turn_said_with_the_other_voice_takes_the_one_sound_of_both(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09: in a debate "Common sense?" was said with the other voice's "common sense."
    at once, so the letters were there once; the one search put it after them, where none of its
    letters were, and its own search, which found them, was refused as the other voice's words:
    the reply came up 0.9 s late on silence (the bench's en_debate_overlap with jitter). Only a
    turn whose letters the first search found where it waited has two sounds to tell apart."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    said = [("whiskey", 0.5), ("alpha", 1.0), ("bravo", 1.5)]
    engine.emitter, engine.roman = emitter(said), Roman()  # type: ignore[assignment]
    host = Utterance(0.3, 2.0, "S1", "whiskey alpha bravo")
    reply = Utterance(1.1, 2.5, "S2", "alpha bravo")
    words = engine.align(np.zeros(16), [host, reply], "English")
    assert [round(w.start, 1) for w in words][3:] == [1.0, 1.5]
    assert guards.counts()["align.unwaited"] == 1 and guards.counts()["align.echoed"] == 0
