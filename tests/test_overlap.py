"""A short reply said inside another speaker's turn ("Really?" while the host talks on) is timed
where it was said, not pushed after the end of that turn."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.asr.fuse import fuse
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

LETTERS = "abcdefghijklmnopqrstuvwxyz"
SECONDS = 12.0
HOST = Utterance(0.0, 10.0, "S1", "alpha bravo delta echo")
REPLY = Utterance(4.8, 5.6, "S2", "really")


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


def engine(said: dict[str, float], monkeypatch: pytest.MonkeyPatch) -> AlignEngine:
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    built = AlignEngine.__new__(AlignEngine)
    built.emitter, built.roman = Emitter(said), Roman()  # type: ignore[assignment]
    return built


def test_a_reply_inside_another_turn_is_timed_where_it_was_said(
        monkeypatch: pytest.MonkeyPatch) -> None:
    said = {"alpha": 1.0, "bravo": 3.0, "really": 5.0, "delta": 7.0, "echo": 9.0}
    words = engine(said, monkeypatch).align(np.zeros(16), [HOST, REPLY], "English")
    assert [w.text for w in words] == ["alpha", "bravo", "delta", "echo", "really"]
    times = {w.text: w.start for w in words}
    assert abs(times["really"] - 5.0) < 0.2 and abs(times["echo"] - 9.0) < 0.2


def test_the_second_opinion_can_place_a_reply_inside_another_turn() -> None:
    host = Utterance(0.0, 10.0, "S1", "one two three four")
    reply = Utterance(5.0, 5.5, "S2", "Really?")
    aligned = [Word("one", 0.5, 0.8, "S1"), Word("two", 3.0, 3.3, "S1"),
               Word("three", 7.0, 7.3, "S1"), Word("four", 9.4, 9.7, "S1"),
               Word("Really?", 9.8, 10.2, "S2")]
    heard = [Word("one", 0.5, 0.8), Word("two", 3.0, 3.3), Word("Really?", 5.0, 5.4),
             Word("three", 7.0, 7.3), Word("four", 9.4, 9.7)]
    fused = fuse(aligned, [host, reply], heard)
    assert [w.text for w in fused] == ["one", "two", "Really?", "three", "four"]
    assert next(w for w in fused if w.speaker == "S2").start == 5.0


def test_two_long_turns_said_at_once_stay_whole() -> None:
    """Interleaving them by time made a line for each word (2026-10-29)."""
    from tarjim.asr.fuse import slotted

    asked = [Word(w, 234.7 + k * 0.4, 234.9 + k * 0.4, "S2")
             for k, w in enumerate(["Is", "that", "kind", "of", "what", "you're", "saying?"])]
    answer = [Word(w, 234.8 + k * 0.3, 235.0 + k * 0.3, "S1")
              for k, w in enumerate(["So", "so", "so", "I", "think", "the", "level"])]
    from tarjim.asr.align import overlapping
    from tarjim.listen.gemini_listen import Utterance

    turns = [Utterance(234.7, 237.5, "S2", "Is that kind of what you're saying?"),
             Utterance(234.8, 237.0, "S1", "So so so I think the level")]
    assert overlapping(turns) == [False, False]
    assert slotted(asked + answer, []) == asked + answer


def test_a_question_answered_over_its_end_still_shows_long_enough() -> None:
    from tarjim.models import Cue
    from tarjim.rules import DEFAULT_RULES
    from tarjim.segment import fit_timing

    question = Cue(234.74, 237.78, text="هذا قصدك؟")
    answer = Cue(234.8, 239.0, text="أشوف التدخل البشري كان هائل")
    fitted = fit_timing([question, answer], DEFAULT_RULES)
    assert fitted[0].end - fitted[0].start >= DEFAULT_RULES.min_duration
    assert fitted[1].start >= fitted[0].end and fitted[1].end >= 239.0
