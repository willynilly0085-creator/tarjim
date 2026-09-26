from typing import Any

import pytest

from tarjim import gemini_client
from tarjim.gemini_client import MODELS, GeminiClient, QuotaExhausted, pause_for


class Refusal(Exception):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.code = 429


DAILY_TEXT = "{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'retryDelay': '47s'}"


def bare_client(outcomes: dict[str, Any]) -> GeminiClient:
    client = GeminiClient.__new__(GeminiClient)
    client.spent, client.model_used = set(), ""

    def call(model: str, *_: Any) -> Any:
        outcome = outcomes.get(model, Refusal(DAILY_TEXT))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client.call = call  # type: ignore[method-assign]
    return client


def test_daily_quota_moves_on_to_the_next_model_without_waiting(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: pytest.fail("should not wait"))
    client = bare_client({MODELS[2]: ["ok"]})
    assert client.ask("p", b"", {}) == ["ok"]
    assert client.spent == set(MODELS[:2])


def test_every_model_used_up_says_so_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    with pytest.raises(QuotaExhausted):
        bare_client({}).ask("p", b"", {})


def test_per_minute_limit_waits_the_time_google_asks_for() -> None:
    assert pause_for(Refusal("{'retryDelay': '47s'}")) == 47.0
    assert pause_for(Refusal("{'retryDelay': '900s'}")) == 90.0
