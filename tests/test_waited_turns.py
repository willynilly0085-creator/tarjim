"""A long turn begun over the end of another is timed where it was said, not after the other
one's last letters (2026-11-08). The one in-order search made "That is far too simple." wait for
the end of the turn it was said over: 0.55 s late on every en_debate_overlap run."""
from dataclasses import replace
from itertools import pairwise
from typing import Any

import numpy as np
import pytest

from tarjim import guards
from tarjim.asr import vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.asr.waited import cleared
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


def test_a_line_heard_again_over_a_turn_where_it_is_not_said_is_not_moved(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A listener's loop (2026-11-09): "alpha bravo", said once at 0.5 s, heard again at 4.7 s
    over the host's last word. Searched on its own inside its own time it took the host's
    letters, with a likelihood of 0.19 to 0.42, and on the bench hid "on four days" and "on the
    bus this time" under the copy. Its letters are not heard there: the first times stay."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(SAID), Roman()  # type: ignore[assignment]
    again = Utterance(4.7, 5.9, "S1", "alpha bravo")
    words = engine.align(np.zeros(16), [HOST, again], "English")
    assert [w.text for w in words] == ["alpha", "bravo", "whiskey", "alpha", "bravo"]
    assert words[3].start >= words[2].end
    assert guards.counts()["align.unwaited"] == 0


def test_a_line_not_heard_where_a_turn_searched_again_runs_on_goes_after_it(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """mixed_en_ar's loop (2026-11-09): the guest's reply, said over the host's line heard again,
    searched on its own runs on 1 s over the next copy of that line, which the one search had
    put on the reply's last words where none of its letters are heard. Both were shown in one
    dialogue subtitle cut to 0.9 s; cutting the reply back instead showed its last words before
    they were said. The reply keeps its own times and the copy goes after it, before the next
    line, in its order."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    said = SAID | {"kilo": 9.0}
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(said), Roman()  # type: ignore[assignment]
    turn = Utterance(4.7, 7.5, "S2", "ox india juliet")
    again = Utterance(5.6, 6.4, "S1", "alpha bravo alpha bravo alpha")
    words = engine.align(np.zeros(16), [HOST, turn, again, Utterance(8.9, 9.5, "S1", "kilo")],
                         "English")
    assert [w.text for w in words[3:6]] == ["ox", "india", "juliet"]
    assert abs(words[3].start - 4.7) < 0.1 and abs(words[5].start - 7.0) < 0.1
    copy = words[6:11]
    assert copy[0].start >= words[5].end - 1e-6 and copy[-1].end <= words[11].start + 1e-6
    assert all(a.end <= b.start + 1e-6 for a, b in pairwise(copy))
    assert guards.counts()["align.unwaited"] == 1


def test_a_turn_searched_again_runs_on_over_a_line_heard_there(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Two voices at once (2026-11-09): "And what about students" runs on over "They can use the
    school", whose letters are heard where the one search put them. Its own times stay."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    said = SAID | {"kilo": 7.2, "lima": 7.8, "mike": 8.3, "oscar": 8.8, "papa": 9.3}
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(said), Roman()  # type: ignore[assignment]
    turn = Utterance(4.7, 7.5, "S2", "ox india juliet")
    reply = Utterance(7.2, 9.6, "S1", "kilo lima mike oscar papa")
    words = engine.align(np.zeros(16), [HOST, turn, reply], "English")
    assert [w.text for w in words[3:7]] == ["ox", "india", "juliet", "kilo"]
    assert abs(words[3].start - 4.7) < 0.1 and abs(words[6].start - 7.2) < 0.1
    assert words[5].end > words[6].start + 0.05
    assert guards.counts()["align.unwaited"] == 1


def test_a_line_cleared_with_room_after_the_turn_keeps_its_length() -> None:
    """With time before the next line, the copy moves on whole (2026-11-09); a line with no
    letters heard or not inside the turn stays where it is."""
    turn = [Word("ox", 4.7, 5.0, "S2", score=0.9), Word("india", 5.2, 6.0, "S2", score=0.9)]
    copy = [Word("alpha", 5.5, 5.9, "S1", score=0.01), Word("bravo", 6.0, 6.4, "S1", score=0.02)]
    moved = cleared(turn, copy, Word("kilo", 9.0, 9.4, "S1", score=0.9))
    assert [(w.start, w.end) for w in moved] == pytest.approx([(6.0, 6.4), (6.5, 6.9)])
    assert cleared(turn, [replace(w, score=None) for w in copy], None) == copy
    later = [replace(w, start=w.start + 1, end=w.end + 1) for w in copy]
    assert cleared(turn, later, None) == later
