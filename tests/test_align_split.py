"""A group of lines the aligner cannot follow as a whole is cut at its longest silence and each
half is tried on its own; only what still cannot be followed is spread evenly over its line, and
that is written to the log once (2026-11-08). Before, one line with too many letters for its sound
spread every line of its group evenly, with nothing in the log."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import vad
from tarjim.asr.align import AlignEngine, quietest
from tarjim.asr.ctc import FRAME
from tarjim.listen.gemini_listen import Utterance

LETTERS = "abcdefghijklmnopqrstuvwxyz"
SECONDS = 40.0
CROWDED = " ".join(["abcdefghij"] * 200)  # 2000 letters said in one second: cannot be followed


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


def engine(said: dict[str, float], monkeypatch: pytest.MonkeyPatch,
           speech: list[tuple[float, float]]) -> AlignEngine:
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: speech)
    built = AlignEngine.__new__(AlignEngine)
    built.emitter, built.roman = Emitter(said), Roman()  # type: ignore[assignment]
    return built


def test_a_line_that_cannot_be_followed_leaves_the_others_aligned(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    lines = [Utterance(0.5, 3.5, "S1", "alpha"), Utterance(30.0, 31.0, "S1", CROWDED)]
    aligner = engine({"alpha": 2.0}, monkeypatch, [(0.0, 4.0), (29.0, 32.0)])
    words = aligner.align(np.zeros(16), lines, "English")
    assert len(words) == 201
    assert abs(words[0].start - 2.0) < 0.2
    assert words[1].start == 30.0 and abs(words[-1].end - 31.0) < 1e-6
    out = capsys.readouterr().out
    assert out.count("spread evenly") == 1
    assert "200 words" in out and "30.0-31.0 s" in out


def test_a_group_is_cut_at_its_longest_silence() -> None:
    speech = np.ones(int(SECONDS / FRAME), dtype=bool)
    speech[int(12.0 / FRAME):int(18.0 / FRAME)] = False
    group = [Utterance(0.0, 5.0, "S1", "a"), Utterance(6.0, 11.0, "S1", "b"),
             Utterance(19.0, 22.0, "S1", "c"), Utterance(22.5, 25.0, "S1", "d")]
    assert quietest(group, speech) == 2


def test_text_without_letters_is_spread_once_without_cutting(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    lines = [Utterance(1.0, 2.0, "S1", "♪ ♪"), Utterance(5.0, 6.0, "S1", "♪")]
    words = engine({}, monkeypatch, [(0.0, SECONDS)]).align(np.zeros(16), lines, "English")
    assert [w.start for w in words] == [1.0, 1.5, 5.0]
    out = capsys.readouterr().out
    assert out.count("spread evenly") == 1 and "3 words" in out and "1.0-6.0 s" in out
