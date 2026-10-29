from types import SimpleNamespace
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
    client.spent, client.model_used, client.cooling, client.refused = set(), "", {}, set()
    client.models, client.slow = list(MODELS), set()

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


class Busy(Exception):
    code = 503


class Bad(Exception):
    code = 400


class ReadTimeout(Exception):
    pass


def test_the_model_the_person_picked_is_asked_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client, "setting", lambda _name: "gemini-3.5-flash")
    assert gemini_client.chosen_first()[:2] == ["gemini-3.5-flash", MODELS[0]]
    monkeypatch.setattr(gemini_client, "setting", lambda _name: "")
    assert gemini_client.chosen_first() == MODELS


def test_a_picked_model_that_cannot_answer_gives_way_to_the_usual_ones(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    client = bare_client({"picked-image-model": Bad("not a text model"), MODELS[0]: ["ok"]})
    client.models = ["picked-image-model", *MODELS]
    assert client.ask("p", None, {}) == ["ok"]


def test_an_overloaded_or_slow_model_is_left_for_the_next_one_at_once(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client, "STALLED", {})
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: pytest.fail("should not wait"))
    asked: list[str] = []
    outcomes = {MODELS[0]: ReadTimeout(), MODELS[1]: Busy(), MODELS[2]: ["ok"]}
    client = bare_client(outcomes)
    real_call = client.call
    client.call = lambda model, *rest: asked.append(model) or real_call(model, *rest)  # type: ignore[method-assign]
    assert client.ask("p", None, {}) == ["ok"]
    assert asked == MODELS[:3] and client.slow == {MODELS[0]}


def test_text_is_translated_with_short_thinking_and_no_silent_retries(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from google import genai

    made: dict[str, Any] = {}
    monkeypatch.setattr(genai, "Client", lambda **options: made.update(options))
    GeminiClient(api_key="AIzaSyA1234567890abcdefghij")
    assert made["http_options"].retry_options.attempts == 1
    assert gemini_client.thinking("gemini-3.8-flash", listening=False) is not None
    assert gemini_client.thinking("gemini-3.8-flash", listening=True) is None
    assert gemini_client.thinking("gemini-2.5-flash", listening=False) is None


def sent_config(monkeypatch: pytest.MonkeyPatch, listening: bool) -> Any:
    from google import genai

    sent: dict[str, Any] = {}
    answer = SimpleNamespace(text="[]")
    models = SimpleNamespace(generate_content=lambda **kw: sent.update(kw) or answer)
    monkeypatch.setattr(genai, "Client", lambda **_options: SimpleNamespace(models=models))
    client = GeminiClient(api_key="AIzaSyA1234567890abcdefghij", listening=listening)
    client.call("gemini-3.8-flash", "p", b"sound", {})
    return sent["config"]


def test_translating_with_the_clip_sound_thinks_briefly_and_gives_way_in_90_seconds(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config = sent_config(monkeypatch, listening=False)
    assert config.thinking_config is not None
    assert config.http_options.timeout == gemini_client.ANSWER_MS
    client = bare_client({})
    client.listening = False
    minute = bytes(gemini_client.SOUND_BYTES_PER_SECOND * 60)
    assert client.limit_ms(minute) == 120_000
    assert client.limit_ms(minute * 10) == gemini_client.REQUEST_MS


def test_listening_keeps_full_thinking_and_the_long_limit(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config = sent_config(monkeypatch, listening=True)
    assert config.thinking_config is None
    assert config.http_options.timeout == gemini_client.REQUEST_MS
