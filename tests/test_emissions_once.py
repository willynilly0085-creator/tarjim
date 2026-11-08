"""The aligner hears a clip's letters once: lines timed again in a stretch of the clip and the
check after timing read them from the whole clip's letters, never from hearing a slice again
(2026-11-08: a slice pushed the whole clip out of the cache, and the check then heard all of it
once more, up to four whole-clip passes on a computer without a graphics card)."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import align, vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME, Letters, piece
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.timing import Timer

RATE = 16000
HOP = int(RATE * FRAME)
SECONDS = 40.0
LETTERS = "abcdefghijklmnopqrstuvwxyz"
VOCAB = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3} | {ch: 4 + k for k, ch in enumerate(LETTERS)}
SAID = {"alpha": 3.0, "bravo": 25.0}


def clip() -> np.ndarray:
    """Each frame's samples hold the letter said in it, so a slice is heard like the whole."""
    labels = np.zeros(int(SECONDS / FRAME), dtype=np.float32)
    for word, at in SAID.items():
        for k, ch in enumerate(word):
            first = int(at / FRAME) + 3 * k
            labels[first:first + 3] = VOCAB[ch]
    return np.repeat(labels, HOP)


class Hearing:
    def __init__(self) -> None:
        self.passes: list[float] = []

    def __call__(self, wav: Any) -> np.ndarray:
        self.passes.append(len(wav) / RATE)
        labels = np.asarray(wav, dtype=np.float32)[::HOP].astype(np.int64)
        probs = np.full((len(labels), len(VOCAB)), 0.02 / len(VOCAB))
        probs[np.arange(len(labels)), labels] = 0.98
        return np.log(probs)


class Emitter:
    vocab = VOCAB

    def __init__(self, hearing: Hearing) -> None:
        self.emissions = Letters(hearing)


class Roman:
    def romanize_string(self, text: str) -> str:
        return text


@pytest.fixture
def hearing(monkeypatch: pytest.MonkeyPatch) -> Hearing:
    heard = Hearing()
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(heard), Roman()  # type: ignore[assignment]
    monkeypatch.setattr(align, "shared_aligner", lambda: engine)
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    return heard


def test_a_stretch_and_the_check_read_the_letters_heard_once(
        hearing: Hearing, capsys: pytest.CaptureFixture[str]) -> None:
    lines = [Utterance(2.5, 4.5, "S1", "alpha"), Utterance(24.5, 26.5, "S1", "bravo")]
    timer = Timer(clip(), RATE, "English", [])
    whole = timer.whole(lines)
    again = timer.part([lines[1]])
    assert abs(again[0].start - 25.0) < 0.1 and abs(again[0].end - 25.3) < 0.1
    assert timer.agreement(whole) == 1.0
    assert Timer(timer.wav, RATE, "English", []).agreement(again) == 1.0
    assert hearing.passes == [SECONDS]
    told = [line for line in capsys.readouterr().out.splitlines() if "clip's letters" in line]
    assert told == ["timing: the aligner heard the clip's letters 1 time(s)"] * 2


def test_a_stretch_starts_on_a_frame_of_the_whole_clip() -> None:
    sound = clip()
    stretch = piece(sound, RATE, 19.507, 31.5)
    assert stretch.start == pytest.approx(19.5)
    assert len(stretch) == round((31.5 - 19.5) * RATE)
    assert float(stretch[0]) == float(sound[round(19.5 * RATE)])
    heard = Hearing()
    letters = Letters(heard)
    assert np.array_equal(letters(stretch), letters(sound)[975:1575])
    assert heard.passes == [SECONDS]


def test_only_the_last_clip_is_kept() -> None:
    """A weak computer keeps one clip's letters, not one for every sound it was asked about."""
    heard = Hearing()
    letters = Letters(heard)
    first, second = clip(), clip()[: 10 * RATE]
    letters(first)
    letters(second)
    letters(first)
    assert heard.passes == [SECONDS, 10.0, SECONDS]
