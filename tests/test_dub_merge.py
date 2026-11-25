"""2026-11-25: Meta's assistant was split in two by the listener; 2.7 s of it became a fourth
person and two of its lines were dubbed in another voice, heard back as English."""
from pathlib import Path

import numpy as np
import pytest

from tarjim.dub import merge
from tarjim.dub.lines import Line


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    found: np.ndarray = vector / np.linalg.norm(vector)
    return found


MARK, ASSISTANT, JOANNA = unit(1, 0, 0), unit(0, 1, 0), unit(0, 0.2, 1)
SPLIT = unit(0.3, 0.8, 0.1)  # the assistant's 2.7 s, nearer it than anyone


def test_a_short_voice_goes_to_the_person_it_sounds_like() -> None:
    found = {"voice1": (12.0, MARK), "voice2": (11.1, ASSISTANT), "voice3": (8.2, JOANNA),
             "voice4": (2.7, SPLIT)}
    assert merge.moves(found) == {"voice4": "voice2"}


def test_a_short_voice_like_nobody_stays_its_own() -> None:
    found = {"voice1": (12.0, MARK), "voice2": (2.0, unit(0, 0, -1))}
    assert merge.moves(found) == {}


def test_its_lines_take_that_voice_and_its_sample_is_dropped(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.asr import voiceprint

    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    monkeypatch.setattr(merge, "prints", lambda samples: {
        "voice2": (11.1, ASSISTANT), "voice4": (2.7, SPLIT)})
    samples = {"voice2": Path("voice2.wav"), "voice4": Path("voice4.wav")}
    lines = [Line(64.8, 67.0, "voice4", "أوه، حلو."), Line(70.6, 72.0, "voice2", "وتفهم")]
    kept, said = merge.merged(samples, lines)
    assert list(kept) == ["voice2"] and [line.speaker for line in said] == ["voice2", "voice2"]


def test_without_voice_prints_the_dub_goes_on_as_it_was(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.asr import voiceprint

    monkeypatch.setattr(voiceprint, "fetched", lambda: True)

    def broken(_samples: dict[str, Path]) -> dict[str, tuple[float, np.ndarray]]:
        raise RuntimeError("the voice print model failed")

    monkeypatch.setattr(merge, "prints", broken)
    samples = {"voice4": Path("voice4.wav")}
    lines = [Line(64.8, 67.0, "voice4", "أوه")]
    assert merge.merged(samples, lines) == (samples, lines)
