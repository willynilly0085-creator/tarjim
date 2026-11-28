"""Gemini's dubbing voices through a Vertex AI key (2026-11-28).

The owner's voices went to a second, paid key while his Vertex credit sat unused, because tarjim
spoke only through the Interactions API, which Vertex lacks. Vertex speaks through generateContent.
"""
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from tarjim.dub import gemini_voice
from tarjim.google_ai import GLOBAL

SOUND = np.ones(4, dtype=np.float32)


class Door:
    def __init__(self, refusals: list[Exception]) -> None:
        self.refusals = refusals
        self.asked: list[dict[str, Any]] = []
        self.models = self
        self.interactions = self

    def generate_content(self, **asked: Any) -> Any:
        self.asked.append(asked)
        if self.refusals:
            raise self.refusals.pop(0)
        data = SimpleNamespace(data=b"RIFF")
        part = SimpleNamespace(inline_data=data)
        return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])

    def create(self, **asked: Any) -> Any:
        self.asked.append({"interactions": asked})
        return SimpleNamespace(output_audio=SimpleNamespace(data="UklGRg=="))


def voices(monkeypatch: pytest.MonkeyPatch, key: str, door: Door) -> Any:
    monkeypatch.setattr(gemini_voice, "api_key", lambda _name: key)
    monkeypatch.setattr(gemini_voice, "google_client", lambda _key, _options: door)
    monkeypatch.setattr(gemini_voice, "decode", lambda _data: SOUND)
    monkeypatch.setattr(gemini_voice, "cast", lambda _refs: {"": "Algenib"})
    return gemini_voice.GeminiVoices({}, "ar")


def test_a_vertex_key_speaks_through_generate_content(monkeypatch: pytest.MonkeyPatch) -> None:
    door = Door([])
    assert voices(monkeypatch, "AQ.vertex", door).record("هلا", "Algenib") is SOUND
    asked = door.asked[0]
    assert asked["model"] == gemini_voice.MODELS[0]
    assert asked["config"].speech_config.voice_config.prebuilt_voice_config.voice_name == "Algenib"
    assert asked["contents"].parts[0].speech_metadata.style.startswith("natural")


def test_a_gemini_api_key_still_speaks_through_interactions(
        monkeypatch: pytest.MonkeyPatch) -> None:
    door = Door([])
    voices(monkeypatch, "AIza-studio", door).record("هلا", "Kore")
    assert "interactions" in door.asked[0]


class Missing(Exception):
    code = 404

    def __str__(self) -> str:
        return ("Publisher model `projects/42/locations/europe-west1/publishers/google/models/"
                f"{gemini_voice.MODELS[0]}` was not found")


def test_a_voice_model_the_region_lacks_is_asked_at_the_global_place(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tarjim.google_ai.GLOBAL", GLOBAL.copy())
    door = Door([Missing()])
    voices(monkeypatch, "AQ.vertex", door).record("هلا", "Algenib")
    assert door.asked[1]["model"].startswith("projects/42/locations/global/")
