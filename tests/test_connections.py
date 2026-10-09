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


def test_only_running_local_programs_are_listed_even_without_a_model(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_servers, "alive", lambda server, _url: server in ("ollama", "jan"))
    monkeypatch.setattr(local_servers, "models_of",
                        lambda server, _url: ["m1"] if server == "ollama" else [])
    found = {s.id: s.models for s in local_servers.discover()}
    assert found == {"ollama": ["m1"], "jan": []}


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


def test_an_install_that_died_is_reported_as_failed(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import assistant_setup

    state = tmp_path / "install.json"
    state.write_text(json.dumps({"state": "installing", "pid": 999999999}))
    monkeypatch.setattr(assistant_setup, "STATE", state)
    monkeypatch.setattr(assistant_setup, "running", lambda: False)
    monkeypatch.setattr(assistant_setup, "server_command", lambda: [])
    assert assistant_setup.status()["state"] == "failed"
    import os

    state.write_text(json.dumps({"state": "installing", "pid": os.getpid()}))
    assert assistant_setup.status()["engine"] == "installing"


def test_the_windows_launch_line_carries_the_settings_and_the_log(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import installer

    monkeypatch.setenv("PYTHONPATH", "C:/plugin")
    monkeypatch.delenv("TARJIM_HOME", raising=False)
    command = ["python", "-m", "tarjim.installer", "file:///x"]
    line = installer.windows_line(command, tmp_path / "i.log")
    assert line.startswith('cmd /d /s /c "set "PYTHONPATH=C:/plugin"&& python -m tarjim.installer')
    assert line.endswith(f'>> "{tmp_path / "i.log"}" 2>&1"')


def test_an_install_just_requested_counts_as_installing(tmp_path: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    from tarjim import assistant_setup

    state = tmp_path / "install.json"
    state.write_text(json.dumps({"state": "installing", "pid": 0, "at": time.time()}))
    monkeypatch.setattr(assistant_setup, "STATE", state)
    monkeypatch.setattr(assistant_setup, "running", lambda: False)
    monkeypatch.setattr(assistant_setup, "server_command", lambda: ["tarjim-serve"])
    assert assistant_setup.status()["engine"] == "installing"


def test_the_install_lets_uv_pick_the_graphics_card_build() -> None:
    from tarjim.installer import install_command

    command = install_command("uv", "file:///plugin")
    assert command[command.index("--torch-backend") + 1] == "auto"
    assert command[-1] == "tarjim[dub] @ file:///plugin"


def test_listening_can_only_be_a_known_engine_that_is_ready(home: Path) -> None:
    assert not connections.remember_choice({"provider": "codex", "listen": "evil"})
    assert not connections.remember_choice({"provider": "codex", "listen": "gemini"})
    assert connections.remember_choice({"provider": "codex", "listen": "local"})
    assert config.setting("listen_provider") == "local"


def test_claude_models_are_named_like_the_claude_app_and_the_lightest_is_suggested(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.engines import subscription_models

    (tmp_path / ".claude.json").write_text(json.dumps({"additionalModelOptionsCache": [
        {"value": "claude-fable-5[1m]", "label": "Fable"},
        {"value": "claude-mythos-6", "label": "Mythos"},
        {"value": "cc-update-required-2", "label": "Opus 5.5 (disabled)", "disabled": True}]}))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    models = subscription_models.claude_models()
    latest = [m["name"] for m in models if m["group"] == "latest"]
    assert latest == ["Opus 5.5", "Fable 5.1", "Sonnet 5.5", "Haiku 5.5"]
    assert [m["id"] for m in models if m["suggested"]] == ["claude-sonnet-5-5"]
    ids = [m["id"] for m in models]
    assert "claude-mythos-6" in ids and "claude-fable-5[1m]" not in ids
    assert "cc-update-required-2" not in ids
    assert connections.MODEL_NAME.match("claude-fable-5-1[1m]")


def test_opencode_go_is_told_who_is_asking_and_other_providers_are_not(home: Path) -> None:
    from tarjim.engines.compatible import headers

    go = headers("sk-go", "opencode_go")
    assert go["Authorization"] == "Bearer sk-go" and go["User-Agent"].startswith("tarjim/")
    assert headers("sk-go", "opencode_go")["x-opencode-session"] == go["x-opencode-session"]
    assert headers("sk-x", "deepseek") == {"Authorization": "Bearer sk-x"}


def test_only_opencode_go_models_that_speak_chat_completions_are_offered(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.engines import provider_models

    config.save("opencode_go_api_key", "sk-go-1234567890abcdef")
    monkeypatch.setattr(provider_models, "web_rows", lambda _url, _headers: [
        ("deepseek-v4.1-flash", "", ""), ("minimax-m3", "", ""), ("glm-5.3", "", ""),
        ("gpt-6-luna", "", "")])
    ids = [m["id"] for m in provider_models.models_for("opencode_go")]
    assert sorted(ids) == ["deepseek-v4.1-flash", "glm-5.3"]
