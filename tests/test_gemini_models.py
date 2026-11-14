"""Which Gemini model is asked, and what a model a key does not have costs (2026-11-14)."""
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim import gemini_client
from tarjim.gemini_client import MODELS, OFFERED, GeminiClient, thinking


class NotOffered(Exception):
    code = 404


def test_a_model_the_key_does_not_have_is_passed_over_at_once(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A 404 was taken for a busy model and asked three times over, with a pause each time."""
    asked: list[str] = []

    def call(self: GeminiClient, model: str, *_rest: Any) -> Any:
        asked.append(model)
        if model == "gemini-4-carbon":
            raise NotOffered("Publisher model was not found or your project does not have access")
        return ["ok"]

    monkeypatch.setattr(gemini_client, "setting", lambda name: "gemini-4-carbon")
    monkeypatch.setattr(gemini_client, "google_client", lambda *_a: SimpleNamespace())
    monkeypatch.setattr(gemini_client, "gemini_key", lambda: "key")
    monkeypatch.setattr(GeminiClient, "call", call)
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: pytest.fail("no waiting"))
    assert GeminiClient().ask("p", None, {}) == ["ok"]
    assert asked == ["gemini-4-carbon", MODELS[0]]


def test_the_newer_models_are_offered_and_never_asked_unless_picked() -> None:
    assert {"gemini-4-carbon", "gemini-4-argon", "gemini-4-hydrogen"} <= set(OFFERED)
    assert not set(OFFERED) & set(MODELS)


@pytest.mark.parametrize("model", ["gemini-3.8-flash", "gemini-4-hydrogen"])
def test_translating_thinks_little_and_listening_as_the_model_does(model: str) -> None:
    assert thinking(model, listening=True) is None
    assert thinking(model, listening=False) is not None
