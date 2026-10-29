"""Engines tell a real failure from a good answer, remember only what they really learned, and
give a computer's own model the time and room a long batch needs."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, gemini_client
from tarjim.engines import antigravity, compatible, local_servers, ollama, provider_models, web
from tarjim.gemini_client import MODELS, GeminiClient, QuotaExhausted
from tarjim.models import Cue, Word
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief

SCHEMA = {"type": "array", "items": {"type": "object"}}
LISTING = "gemini-3.8-flash-high\tGemini 3.8 Flash (High)\ngemini-3.8-flash-low\tFlash (Low)\n"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    antigravity.forget()


def test_a_translation_that_mentions_signing_in_is_still_a_translation() -> None:
    said = [{"id": 1, "text": "Please sign in to continue."}]
    printed = json.dumps({"status": "SUCCESS", "structured_output": said})
    assert antigravity.answer_of(0, printed, "") == said
    failed = json.dumps({"status": "ERROR", "error": "quota used up",
                         "response": "you must sign in"})
    with pytest.raises(web.EngineError, match="quota"):
        antigravity.answer_of(1, failed, "")


def test_a_failed_model_listing_is_not_remembered(monkeypatch: pytest.MonkeyPatch) -> None:
    printed = [""]
    monkeypatch.setattr(antigravity, "listing", lambda: printed[0])
    assert antigravity.light_variant("gemini-3.8-flash-high") == "gemini-3.8-flash-high"
    assert antigravity.hearing_model() == ""
    printed[0] = LISTING
    assert antigravity.light_variant("gemini-3.8-flash-high") == "gemini-3.8-flash-low"
    assert antigravity.hearing_model() == "gemini-3.8-flash-low"
    printed[0] = "gemini-4-flash-low\tFlash 4 (Low)\n"
    assert antigravity.hearing_model() == "gemini-3.8-flash-low"
    provider_models.forget()
    assert antigravity.hearing_model() == "gemini-4-flash-low"


def test_ollama_gets_room_and_time_for_a_long_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def post(_provider: str, _url: str, _headers: dict[str, str], **payload: Any) -> Any:
        sent.update(payload)
        return {"message": {"content": json.dumps({"result": []})}}

    monkeypatch.setattr(ollama, "post", post)
    ollama.OllamaAsker().ask("x" * 20000, None, SCHEMA)
    assert sent["json"]["options"]["num_ctx"] >= 20000 // 2
    assert sent["timeout"] > web.TIMEOUT
    ollama.OllamaAsker().ask("short", None, SCHEMA)
    assert sent["json"]["options"]["num_ctx"] >= 4096


def test_a_local_server_gets_small_batches_and_more_time(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def post(_provider: str, _url: str, _headers: dict[str, str], **payload: Any) -> Any:
        sent.update(payload)
        return {"choices": [{"message": {"content": json.dumps({"result": []})}}]}

    config.save("local_server", "lmstudio")
    monkeypatch.setattr(compatible, "post", post)
    found = local_servers.local_asker()
    assert found is not None and found.most_cues == web.LOCAL_CUES
    found.ask("x" * 20000, None, SCHEMA)
    assert sent["timeout"] > web.TIMEOUT


def test_the_translator_keeps_to_the_engines_batch_size() -> None:
    class Small:
        hears, most_cues = False, 40

        def __init__(self) -> None:
            self.asked = 0

        def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
            self.asked += 1
            return [{"id": n, "text": "مرحبا"} for n in range(1, 41)]

    engine = Small()
    lines = [Cue(t * 2.0, t * 2.0 + 1, [Word("hi", t * 2.0, t * 2.0 + 1)]) for t in range(100)]
    Translator(engine).translate(lines, lambda _s, _e: b"", Brief())
    assert engine.asked == 3


class Failure(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(str(code))
        self.code = code


def failing(outcomes: dict[str, Any]) -> GeminiClient:
    client = GeminiClient.__new__(GeminiClient)
    client.spent, client.model_used, client.cooling, client.refused = set(), "", {}, set()
    client.models, client.slow, client.listening = list(MODELS), set(), False

    def call(model: str, *_: Any) -> Any:
        outcome = outcomes.get(model, Failure(503))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    client.call = call  # type: ignore[method-assign]
    return client


def test_a_model_that_refuses_gives_way_to_the_next(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    client = failing({MODELS[0]: Failure(403), MODELS[1]: Failure(400), MODELS[2]: ["ok"]})
    assert client.ask("p", None, {}) == ["ok"]


def test_a_refused_picked_model_is_not_a_used_up_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_client.time, "sleep", lambda _s: None)
    daily = Failure(429)
    daily.args = ("GenerateRequestsPerDayPerProjectPerModel",)
    client = failing({"picked": Failure(400), **dict.fromkeys(MODELS, daily)})
    client.models = ["picked", *MODELS]
    with pytest.raises(RuntimeError) as caught:
        client.ask("p", None, {})
    assert not isinstance(caught.value, QuotaExhausted)
    assert "picked: 400" in str(caught.value)
