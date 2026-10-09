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
    client.spent, client.model_used, client.cooling = set(), "", {}

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


def test_the_new_plain_wording_of_a_daily_limit_is_recognised() -> None:
    worded = Refusal("Rate limit exceeded for model gemini-3.8-flash (limit: 20 requests per day "
                     "on Free Tier). Please retry in 59s or upgrade your plan.")
    assert gemini_client.used_up_today(worded)
    assert not gemini_client.used_up_today(Refusal("Rate limit exceeded: 5 requests per minute"))


# The wait is a difference of two clock readings, so it can come out a hair over the delay.
ROUNDING = 1e-6


def test_a_busy_model_is_skipped_and_waiting_happens_once_per_round(
        monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(gemini_client.time, "sleep", slept.append)
    busy = Refusal("{'retryDelay': '59s'} 5 requests per minute")
    client = bare_client({model: busy for model in MODELS} | {MODELS[3]: ["ok"]})
    assert client.ask("p", b"", {}) == ["ok"]
    assert slept == []
    calls = {"n": 0}

    def later(model: str, *_: Any) -> Any:
        calls["n"] += 1
        if calls["n"] <= len(MODELS):
            raise busy
        return ["late"]

    client = bare_client({})
    client.call = later  # type: ignore[method-assign]
    assert client.ask("p", b"", {}) == ["late"]
    assert len(slept) == 1 and slept[0] <= 59.0 + ROUNDING


def test_a_request_that_never_answers_gives_up_instead_of_hanging(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from google import genai

    made: dict[str, Any] = {}
    monkeypatch.setattr(genai, "Client", lambda **options: made.update(options))
    GeminiClient(api_key="AIzaSyA1234567890abcdefghij")
    assert made["http_options"].timeout == gemini_client.REQUEST_MS
