"""Which Gemini key tarjim uses, and what the person is told when a key cannot be checked."""
from typing import Any

import pytest
from google.genai import errors

from tarjim import config, keys


def test_the_key_saved_on_the_page_wins_over_one_left_in_the_environment(
        monkeypatch: pytest.MonkeyPatch) -> None:
    saved = {"gemini_api_key": "saved-on-the-page"}
    monkeypatch.setattr(config, "setting", lambda name: saved.get(name, ""))
    monkeypatch.setenv("GEMINI_API_KEY", "left-by-gemini-cli")
    assert config.gemini_key() == "saved-on-the-page"
    assert config.api_key("gemini_api_key") == "saved-on-the-page"
    saved.clear()
    assert config.gemini_key() == "left-by-gemini-cli"  # nothing saved: the environment's is used
    assert config.api_key("openai_api_key") == ""


def test_a_key_only_in_the_environment_counts_as_set_everywhere(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.engines import choice

    monkeypatch.setattr(config, "setting", lambda _name: "")
    monkeypatch.setenv("GEMINI_API_KEY", "left-by-gemini-cli")
    assert choice.has_key("gemini")
    assert keys.status()["gemini"]


class FakeModels:
    def __init__(self, outcome: Exception | None) -> None:
        self.outcome = outcome

    def list(self) -> Any:
        if self.outcome:
            raise self.outcome
        return iter(["gemini-3.8-flash"])


def google_answers(monkeypatch: pytest.MonkeyPatch, outcome: Exception | None) -> None:
    from google import genai

    client = type("Client", (), {"models": FakeModels(outcome)})
    monkeypatch.setattr(genai, "Client", lambda **_options: client())


def refusal(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "x", "status": "X"}})


@pytest.mark.parametrize(("outcome", "verdict"), [
    (None, ""), (refusal(400), "rejected"), (refusal(403), "rejected"),
    (refusal(429), "unreachable"), (refusal(503), "unreachable"), (TimeoutError(), "unreachable")])
def test_only_a_refusal_from_google_is_called_a_bad_key(
        monkeypatch: pytest.MonkeyPatch, outcome: Exception | None, verdict: str) -> None:
    google_answers(monkeypatch, outcome)
    assert keys.gemini_verdict("AIzaSyA1234567890abcdefghij") == verdict


def test_a_key_google_could_not_check_is_not_saved_and_says_why(
        monkeypatch: pytest.MonkeyPatch) -> None:
    google_answers(monkeypatch, refusal(429))
    saved: list[str] = []
    monkeypatch.setattr(keys, "save", lambda name, _value: saved.append(name))
    assert keys.store("gemini", "AIzaSyA1234567890abcdefghij") == "unreachable"
    google_answers(monkeypatch, None)
    assert keys.store("gemini", "AIzaSyA1234567890abcdefghij") == "saved"
    assert saved == ["gemini_api_key"]


def test_the_key_check_keeps_its_client_open_while_google_answers(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from google import genai

    state = {"closed": False}

    class Models:
        def list(self) -> Any:
            def pages() -> Any:
                if state["closed"]:
                    raise RuntimeError("Cannot send a request, as the client has been closed.")
                yield "gemini-3.8-flash"
            return pages()

    class Client:  # like google-genai 2.33: a client nothing holds closes itself
        def __init__(self, **_options: Any) -> None:
            self.models = Models()

        def __del__(self) -> None:
            state["closed"] = True

    monkeypatch.setattr(genai, "Client", Client)
    assert keys.gemini_verdict("AIzaSyA1234567890abcdefghij") == ""
