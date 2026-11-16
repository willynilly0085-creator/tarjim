"""A Vertex key asked with no place is answered from its project's own region; a model that
region lacks is asked again at Google's global location.

On 2026-11-16 the owner's paid key answered every Gemini 4 model with a 404 naming
europe-west1, and tarjim translated with 3.8 Flash instead without a word, while the same key
reached all three at locations/global.
"""
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim import gemini_client, google_ai
from tarjim.gemini_client import MODELS, GeminiClient

PICKED = "gemini-4-hydrogen"
THERE = f"projects/123/locations/global/publishers/google/models/{PICKED}"


class NotThere(Exception):
    def __init__(self, place: str = "europe-west1", code: int = 404) -> None:
        super().__init__(
            f"{code} NOT_FOUND. {{'error': {{'code': {code}, 'message': 'Publisher model "
            f"`projects/123/locations/{place}/publishers/google/models/{PICKED}` was not found "
            "or your project does not have access to it.'}}")
        self.code = code


@pytest.fixture(autouse=True)
def nothing_learnt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google_ai, "GLOBAL", {})
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)


def client_answering(outcomes: list[Any]) -> tuple[GeminiClient, list[str]]:
    """A client whose calls give these outcomes in turn; the names the library would be given."""
    client, asked = GeminiClient.__new__(GeminiClient), []
    client.spent, client.model_used, client.cooling, client.refused = set(), "", {}, set()
    client.models, client.slow = [PICKED, *MODELS], set()

    def call(model: str, *_: Any) -> Any:
        asked.append(google_ai.placed(model))
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client.call = call  # type: ignore[method-assign]
    return client, asked


def test_a_model_the_region_lacks_is_asked_again_at_the_global_location(
        capsys: pytest.CaptureFixture[str]) -> None:
    client, asked = client_answering([NotThere(), ["from hydrogen"], ["again"]])
    assert client.ask("p", None, {}) == ["from hydrogen"]
    assert asked == [PICKED, THERE] and client.refused == set()
    assert "global location" in capsys.readouterr().out
    assert client.ask("p", None, {}) == ["again"] and asked[-1] == THERE  # learnt: no 404 twice


def test_a_model_missing_everywhere_gives_way_to_the_usual_ones() -> None:
    client, asked = client_answering([NotThere(), NotThere("global"), ["from flash"]])
    assert client.ask("p", None, {}) == ["from flash"]
    assert asked == [PICKED, THERE, MODELS[0]] and client.refused == {PICKED}


def test_only_a_404_that_names_a_region_is_taken_for_a_missing_place() -> None:
    studio = NotThere()
    studio.args = ("404 NOT_FOUND. models/gemini-4-hydrogen is not found for API version v1beta",)
    for other in (studio, NotThere(code=403), NotThere("global"), RuntimeError("timed out")):
        assert not google_ai.elsewhere(PICKED, other)
    assert google_ai.placed(PICKED) == PICKED
    assert google_ai.elsewhere(PICKED, NotThere()) and not google_ai.elsewhere(PICKED, NotThere())


def test_the_library_is_given_the_full_name_and_the_log_the_short_one(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from google import genai

    sent: dict[str, Any] = {}
    models = SimpleNamespace(
        generate_content=lambda **kw: sent.update(kw) or SimpleNamespace(text="[]"))
    monkeypatch.setattr(genai, "Client", lambda **_options: SimpleNamespace(models=models))
    client = GeminiClient(api_key="AQ.vertex-key-with-credit")
    assert google_ai.elsewhere(PICKED, NotThere())
    client.call(PICKED, "p", None, {})
    assert sent["model"] == THERE and client.model_used == PICKED
