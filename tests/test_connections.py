import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config
from tarjim.engines import choice, compatible, local_servers
from tarjim.server import assistant_link, connections


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    return tmp_path


def test_choosing_a_subscription_saves_its_model_and_keeps_local_listening(home: Path) -> None:
    assert connections.remember_choice({"provider": "codex", "model": "gpt-5.6-terra"})
    assert config.setting("translate_provider") == "codex"
    assert config.setting("codex_model") == "gpt-5.6-terra"
    assert config.setting("listen_provider") == "local"


def test_listening_follows_a_key_that_can_hear(home: Path) -> None:
    config.save("gemini_api_key", "AIzaSyA1234567890abcdefghij")
    assert connections.listener_for("deepseek") == "gemini"
    assert connections.listener_for("gemini") == "gemini"


def test_bad_choices_are_refused(home: Path) -> None:
    assert not connections.remember_choice({"provider": "nonsense"})
    assert not connections.remember_choice({"provider": "codex", "model": "a b; rm"})
    assert not connections.remember_choice({"provider": "local", "server": "evil"})
    assert config.setting("translate_provider") == ""


def test_a_local_server_other_than_ollama_is_asked_in_openai_format(home: Path) -> None:
    connections.remember_choice({"provider": "local", "server": "lmstudio", "model": "qwen3-8b"})
    found = choice.asker("local")
    assert isinstance(found, compatible.CompatibleAsker)
    assert found.base_url == "http://127.0.0.1:1234/v1" and found.model == "qwen3-8b"


def test_api_providers_send_the_schema_and_read_json_back(home: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_post(_name: str, url: str, headers: dict[str, str], **payload: Any) -> Any:
        sent.update(url=url, headers=headers, body=payload["json"])
        return {"choices": [{"message": {"content": '{"result": [1, 2]}'}}]}

    monkeypatch.setattr(compatible, "post", fake_post)
    config.save("deepseek_api_key", "sk-1234567890abcdefgh")
    config.save("deepseek_model", "deepseek-chat")
    assert choice.asker("deepseek").ask("hi", None, {"type": "array"}) == [1, 2]
    assert sent["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert sent["body"]["model"] == "deepseek-chat"
    assert sent["headers"] == {"Authorization": "Bearer sk-1234567890abcdefgh"}


def test_only_running_local_programs_are_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_servers, "models_of",
                        lambda server, _url: ["m1"] if server in ("ollama", "jan") else [])
    assert [s.id for s in local_servers.discover()] == ["ollama", "jan"]


def test_adding_to_the_claude_app_keeps_other_servers(tmp_path: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "Claude" / "claude_desktop_config.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    done, _ = assistant_link.link("claude-desktop")
    saved = json.loads(settings.read_text(encoding="utf-8"))
    assert done and saved["theme"] == "dark" and "other" in saved["mcpServers"]
    assert saved["mcpServers"]["tarjim"]["args"] == ["-m", "tarjim.assistant"]
