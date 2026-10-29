"""Separating voices from the background works on a few minutes at a time, with the whole sound
kept in the computer's memory rather than on the graphics card, so an hour-long video needs no
more of the card than a short one and running out of memory keeps the original sound."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tarjim.dub import separate
from tarjim.dub.audio import RATE

torch = pytest.importorskip("torch")
pytest.importorskip("demucs")


class Model:
    samplerate = RATE
    sources = ("drums", "bass", "other", "vocals")

    def to(self, _device: str) -> "Model":
        return self

    def eval(self) -> "Model":
        return self


def faked(monkeypatch: pytest.MonkeyPatch, seen: list[dict[str, Any]]) -> None:
    """A model that hears the left channel as voice and the right as everything else."""
    import demucs.apply

    def apply_model(_model: Model, mix: Any, **options: Any) -> Any:
        seen.append({"held on": mix.device.type, "length": mix.shape[-1], **options})
        voice, rest = mix.clone(), mix.clone()
        voice[:, 1], rest[:, 0] = 0, 0
        return torch.stack([rest / 3, rest / 3, rest / 3, voice], dim=1)

    monkeypatch.setattr(separate, "separation_model", Model)
    monkeypatch.setattr(demucs.apply, "apply_model", apply_model)


def test_a_long_sound_is_separated_a_window_at_a_time_from_memory(
        monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []
    faked(monkeypatch, seen)
    monkeypatch.setattr(separate, "WINDOW", 2.0)
    monkeypatch.setattr(separate, "CONTEXT", 0.5)
    rng = np.random.default_rng(1)
    mixture = rng.uniform(-0.5, 0.5, (int(7.3 * RATE), 2)).astype(np.float32)
    mixture -= mixture.mean()
    voices, background = separate.split_voices(mixture)
    assert len(seen) == 4 and all(s["held on"] == "cpu" and "device" in s for s in seen)
    assert max(s["length"] for s in seen) <= 3 * RATE
    assert voices.shape == background.shape == mixture.shape
    np.testing.assert_allclose(voices[:, 0], mixture[:, 0], atol=1e-4)
    np.testing.assert_allclose(background[:, 1], mixture[:, 1], atol=1e-4)
    np.testing.assert_allclose(voices[:, 1], 0, atol=1e-4)


def test_running_out_of_memory_keeps_the_original_sound(monkeypatch: pytest.MonkeyPatch) -> None:
    def too_big(_mixture: np.ndarray) -> Any:
        raise MemoryError

    monkeypatch.setattr(separate, "decode", lambda _video, channels: np.ones((10, channels),
                                                                             np.float32))
    monkeypatch.setattr(separate, "split_voices", too_big)
    stems = separate.separate(Path("clip.mp4"))
    assert not stems.separated and stems.background.shape == (10, 2)
