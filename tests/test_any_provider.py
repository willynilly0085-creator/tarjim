"""Every way to connect offers models that can be used, and odd replies are still understood."""
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tarjim import config
from tarjim.engines import antigravity, app_install, compatible, provider_models, web
from tarjim.engines.catalog import BY_ID, SUBSCRIPTION
from tarjim.engines.choice import SUBSCRIPTIONS, asker
from tarjim.engines.subscription_models import claude_models
from tarjim.server.jobs import classify

SCHEMA = {"type": "array", "items": {"type": "object"}}
GOOD = [{"id": 1, "text": "مرحبا"}]


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def test_gemini_through_antigravity_is_a_subscription_that_tarjim_can_install() -> None:
    found = BY_ID["antigravity"]
    assert found.method == SUBSCRIPTION and "antigravity" in SUBSCRIPTIONS
    assert "Gemini" in found.name and "antigravity" in app_install.NATIVE
    assert isinstance(asker("antigravity"), antigravity.AntigravityAsker)


def test_antigravity_is_asked_once_in_plan_mode_and_its_structured_answer_is_used(
        monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(command: list[str], prompt: str, _folder: str) -> Any:
        seen.update(command=command, stdin=prompt)
        envelope = {"status": "SUCCESS", "response": "", "structured_output": {"result": GOOD}}
        return subprocess.CompletedProcess(command, 0, json.dumps(envelope), "")

    config.save("antigravity_model", "gemini-3-flash")
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    monkeypatch.setattr(antigravity, "run", fake_run)
    assert antigravity.AntigravityAsker().ask("Translate.", None, SCHEMA) == GOOD
    command = seen["command"]
    assert command[:3] == ["agy", "--print", "Translate."] and seen["stdin"] == ""
    assert "--sandbox" in command and "--mode" not in command
    assert command[-2:] == ["--model", "gemini-3-flash"]
    assert "--dangerously-skip-permissions" not in command


SIGNED_OUT = ("Fetching available models...\nError: Please sign in to view available models. "
              "Launch the CLI without arguments to sign in.\n")


LISTING = ("gemini-3.8-flash-high\tGemini 3.8 Flash (High)\n"
           "gemini-3.8-flash-low\tGemini 3.8 Flash (Low)\n"
           "gemini-3.1-pro-high\tGemini 3.1 Pro (High)\nclaude-sonnet-4-6\tClaude Sonnet 4.6\n")


def test_antigravity_lists_the_accounts_models_by_name_and_suggests_the_lightest(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antigravity, "listing", lambda: LISTING)
    models = provider_models.models_for("antigravity")
    assert [m["id"] for m in models] == ["gemini-3.8-flash-high", "gemini-3.8-flash-low",
                                         "gemini-3.1-pro-high", "claude-sonnet-4-6"]
    assert models[1]["name"] == "Gemini 3.8 Flash (Low)"
    assert [m["id"] for m in models if m["suggested"]] == ["gemini-3.8-flash-low"]


def test_a_signed_out_antigravity_lists_nothing_and_is_named_as_a_sign_in_problem() -> None:
    assert antigravity.rows(SIGNED_OUT) == []
    failed = json.dumps({"status": "ERROR", "error": "authentication required"})
    for printed, complaint in ((failed, ""), ("", SIGNED_OUT)):
        with pytest.raises(web.EngineError) as caught:
            antigravity.answer_of(1, printed, complaint)
        assert classify(caught.value) == "signin"
    with pytest.raises(web.EngineError, match="quota"):
        antigravity.answer_of(1, json.dumps({"status": "ERROR", "error": "quota used up"}), "")


def test_claude_offers_its_newest_light_model() -> None:
    latest = [m["id"] for m in claude_models() if m["group"] == "latest"]
    assert "claude-haiku-5-5" in latest and "claude-haiku-4-5" not in latest


class Service:
    """An API that refuses a temperature and a reply format, like some reasoning models."""

    def __init__(self) -> None:
        self.bodies: list[dict[str, Any]] = []

    def post(self, _provider: str, _url: str, _headers: dict[str, str], json: Any) -> Any:
        self.bodies.append(json)
        if "temperature" in json or "response_format" in json:
            raise web.EngineError("deepseek", 400, "temperature is not supported")
        text = "Sure. " + __import__("json").dumps({"result": GOOD}) + " Done."
        return {"choices": [{"message": {"content": text}}]}


def test_an_api_that_refuses_the_extras_is_asked_again_plainly(
        monkeypatch: pytest.MonkeyPatch) -> None:
    service = Service()
    monkeypatch.setattr(compatible, "post", service.post)
    found = compatible.CompatibleAsker("deepseek", "https://api.deepseek.com/v1", "k", "m")
    assert found.ask("Translate.", None, SCHEMA) == GOOD
    assert len(service.bodies) == 2 and "temperature" not in service.bodies[1]


def test_a_reply_with_nothing_in_it_is_an_engine_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compatible, "post", lambda *_a, **_k: {"error": "odd"})
    with pytest.raises(web.EngineError):
        compatible.CompatibleAsker("xai", "https://api.x.ai/v1", "k", "m").ask("T", None, SCHEMA)


def test_a_key_without_a_chosen_model_uses_the_one_the_provider_suggests(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config.save("deepseek_api_key", "sk-test-key")
    listed = [("deepseek-reasoner", "", ""), ("deepseek-chat", "", "")]
    monkeypatch.setattr(provider_models, "api_rows", lambda _provider: listed)
    assert provider_models.model_in_use("deepseek") == "deepseek-chat"
    assert config.setting("deepseek_model") == "deepseek-chat"
    assert compatible.api_asker("deepseek").model == "deepseek-chat"
