"""An assistant in chat can change every setting the page can, and is never handed a secret."""
import asyncio
import inspect
from typing import Any

import pytest

from tarjim import assistant, assistant_settings
from tarjim.server.routes import GET_ROUTES, POST_ROUTES

SECRET_WORDS = ("key", "token", "password", "secret")
# What only the person does: type a key or a bot token, and answer an extension asking to pair.
HUMAN_ONLY = {"save_key", "phone_connect", "phone_forget", "ask_pair", "decide_pair", "pair_state",
              "list_pairs"}
# Routes that serve the page itself or act on the person's screen, not settings.
NOT_SETTINGS = {"ping", "home", "asset", "legacy", "upload", "create_local", "send_output",
                "system", "ui_language", "local_models", "scan_part", "reveal", "play",
                "current_connection", "signed_in", "sign_in_code", "local_program",
                "link_assistant", "phone_link", "key_status"}


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    seen: list[tuple[str, Any]] = []

    def call(path: str, body: Any = None) -> Any:
        seen.append((path, body))
        return {"ok": True}

    monkeypatch.setattr(assistant_settings, "call", call)
    monkeypatch.setattr(assistant, "call", call)
    return seen


def test_no_chat_tool_takes_a_key_or_a_token() -> None:
    tools = asyncio.run(assistant.tarjim.list_tools())
    assert len(tools) >= 32 and {"plan_setup", "use_voice_service", "phone_bot"} <= {
        t.name for t in tools}
    for tool in tools:
        names = " ".join(tool.input_schema.get("properties", {})).lower()
        assert not any(word in names for word in SECRET_WORDS), tool.name


def test_every_setting_the_page_can_change_has_a_chat_tool(asked: list[tuple[str, Any]]) -> None:
    assistant_settings.change_settings(interface_language="ar", start_with_computer="yes",
                                       automatic_updates="no")
    assistant_settings.use_voice_service("groq")
    assistant_settings.prefer_elevenlabs_voice("v-one")
    assistant_settings.phone_bot(result="dub-eleven")
    assistant_settings.phone_bot()
    assistant_settings.apply_setup({"provider": "claude"}, {"provider": "local"}, ["timing"])
    assistant.use_connection("local", "aya-expanse:8b", "ollama")
    assert asked[0] == ("/setup", {"ui_language": "ar", "autostart": True, "auto_update": False})
    assert asked[1] == ("/voices/speech", {"preset": "groq", "url": "", "model": "", "voices": ""})
    assert asked[2:5] == [("/voices/eleven", {"voice": "v-one"}),
                          ("/phone/choices", {"mode": "dub-eleven"}), ("/phone", None)]
    assert asked[5][1]["downloads"] == ["timing"]
    assert asked[6] == ("/connections/use", {"provider": "local", "model": "aya-expanse:8b",
                                             "server": "ollama"})


def test_each_route_that_changes_a_setting_is_reached_by_some_tool() -> None:
    source = inspect.getsource(assistant) + inspect.getsource(assistant_settings)
    for pattern, name in [*GET_ROUTES, *POST_ROUTES]:
        if name in HUMAN_ONLY | NOT_SETTINGS:
            continue
        stem = pattern.pattern.lstrip("^").rstrip("$").split("(")[0].rstrip("/")
        assert f'"{stem}' in source or f"{stem}/" in source, f"no chat tool reaches {name}"
