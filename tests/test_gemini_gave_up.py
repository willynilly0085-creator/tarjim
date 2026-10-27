"""When every Gemini model fails, the error names each one and why.

On 2026-10-27 a free key had used up its day on gemini-3.8-flash to 3.5, and the last model left
was busy. The error listed only that model, four times, so it looked as if tarjim had chosen
gemini-3-flash-preview over 3.8.
"""
from typing import Any

import pytest

from tarjim import gemini_client
from tarjim.gemini_client import MODELS, GeminiClient, QuotaExhausted
from tarjim.server.reasons import classify

DAILY = "{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}"


class Failure(Exception):
    def __init__(self, code: int, text: str = "") -> None:
        super().__init__(text or str(code))
        self.code = code


def failing(outcomes: dict[str, Exception]) -> GeminiClient:
    client = GeminiClient.__new__(GeminiClient)
    client.spent, client.model_used, client.cooling = set(), "", {}
    client.models, client.slow, client.listening = list(MODELS), set(), False

    def call(model: str, *_: Any) -> Any:
        raise outcomes[model]

    client.call = call  # type: ignore[method-assign]
    return client


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)


def test_used_up_models_and_busy_ones_are_all_named() -> None:
    busy = {m: Failure(503) for m in MODELS[-2:]}
    client = failing({**{m: Failure(429, DAILY) for m in MODELS[:-2]}, **busy})
    with pytest.raises(RuntimeError) as caught:
        client.ask("p", b"", {})
    said = str(caught.value)
    assert all(model in said for model in MODELS)
    assert f"{MODELS[0]}: daily quota used up" in said and f"{MODELS[-1]}: 503" in said
    assert classify(caught.value) == "quota"
    # still not "every model used up": listening falls back to the computer's own model
    assert not isinstance(caught.value, QuotaExhausted)


def test_every_model_busy_names_each_once() -> None:
    with pytest.raises(RuntimeError) as caught:
        failing({m: Failure(503) for m in MODELS}).ask("p", b"", {})
    said = str(caught.value)
    assert said.startswith("all Gemini models failed")
    assert [said.count(f"{model}:") for model in MODELS] == [1] * len(MODELS)
