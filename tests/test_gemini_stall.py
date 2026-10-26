"""A model that keeps a job waiting: not asked again in that job unless nothing else answers,
and asked last by the next jobs for a while."""
from typing import Any

import pytest

from tarjim import gemini_client
from tarjim.gemini_client import MODELS, GeminiClient


class Busy(Exception):
    code = 503


def bare_client(outcomes: dict[str, Any]) -> GeminiClient:
    client = GeminiClient.__new__(GeminiClient)
    client.spent, client.model_used, client.cooling = set(), "", {}
    client.models, client.slow = list(MODELS), set()

    def call(model: str, *_: Any) -> Any:
        outcome = outcomes.get(model, Busy())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client.call = call  # type: ignore[method-assign]
    return client


def test_a_model_that_kept_the_job_waiting_is_not_asked_again_and_goes_last_next_time(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client, "STALLED", {})
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    clock = iter(range(0, 10_000, 120))  # every call takes two minutes
    monkeypatch.setattr(gemini_client.time, "monotonic", lambda: float(next(clock)))
    asked: list[str] = []
    client = bare_client({MODELS[0]: Busy(), MODELS[1]: ["ok"]})
    real_call = client.call
    client.call = lambda model, *rest: asked.append(model) or real_call(model, *rest)  # type: ignore[method-assign]
    assert client.ask("p", None, {}) == ["ok"] and client.ask("p", None, {}) == ["ok"]
    assert asked == [MODELS[0], MODELS[1], MODELS[1]]
    assert gemini_client.asked_last_if_stalled(list(MODELS))[-1] == MODELS[0]


def test_a_model_that_kept_us_waiting_is_still_tried_when_nothing_else_answers(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client, "STALLED", {})
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    client = bare_client({model: Busy() for model in MODELS[1:]} | {MODELS[0]: ["late"]})
    client.slow = {MODELS[0]}
    tried: list[str] = []
    real_call = client.call
    client.call = lambda model, *rest: tried.append(model) or real_call(model, *rest)  # type: ignore[method-assign]
    assert client.ask("p", None, {}) == ["late"]
    assert tried == MODELS[1:] * gemini_client.ROUNDS + [MODELS[0]]


def test_a_quick_refusal_is_not_held_against_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client, "STALLED", {})
    client = bare_client({})
    client.note(MODELS[0], Busy(), waited=2.0)
    assert client.slow == set() and gemini_client.STALLED == {}
    assert gemini_client.asked_last_if_stalled(list(MODELS)) == MODELS
