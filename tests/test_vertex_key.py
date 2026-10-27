"""A Vertex AI key (AQ.…) reaches Gemini without the free daily quota, so it goes first.

On 2026-10-27 the owner's free key, saved on tarjim's page, had used up its day on gemini-3.8-flash
while a Vertex key with credit sat unused in VERTEX_API_KEY.
"""
from typing import Any

import pytest

from tarjim import config, keys
from tarjim.engines import provider_models
from tarjim.gemini_client import MODELS
from tarjim.google_ai import google_client

FREE, PAID = "AIza-free-key-on-the-page", "AQ.vertex-key-with-credit"


@pytest.fixture
def saved(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    store = {"gemini_api_key": FREE}
    monkeypatch.setattr(config, "setting", lambda name: store.get(name, ""))
    return store


def test_a_vertex_key_goes_before_the_free_key_saved_on_the_page(
        saved: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "user_variable", {"VERTEX_API_KEY": PAID}.get)
    assert config.gemini_key() == PAID
    assert config.api_key(config.SPOKEN) == FREE  # voices: Vertex has none for tarjim


def test_without_a_vertex_key_nothing_changes(
        saved: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-left-by-gemini-cli")
    assert config.gemini_key() == FREE == config.api_key(config.SPOKEN)


def test_a_vertex_key_pasted_on_the_page_is_used_and_leaves_voices_without_a_key(
        saved: dict[str, str]) -> None:
    saved["gemini_api_key"] = PAID
    assert config.gemini_key() == PAID
    assert config.api_key(config.SPOKEN) == ""


def test_each_kind_of_key_opens_its_own_door() -> None:
    assert google_client(PAID, None)._api_client.vertexai
    assert not google_client(FREE, None)._api_client.vertexai


class Counting:
    def __init__(self) -> None:
        self.asked: list[str] = []
        self.models = self

    def count_tokens(self, model: str, contents: str) -> Any:
        self.asked.append(model)

    def list(self) -> Any:
        raise AssertionError("Vertex AI refuses to list models for a key, even a good one")


def test_a_vertex_key_is_checked_without_listing_models(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Counting()
    monkeypatch.setattr(keys, "google_client", lambda _key, _options: client)
    assert keys.gemini_verdict(PAID) == ""
    assert client.asked == [MODELS[0]]


def test_a_vertex_key_is_offered_tarjims_own_models() -> None:
    assert [row[0] for row in provider_models.gemini_rows(PAID)] == MODELS
