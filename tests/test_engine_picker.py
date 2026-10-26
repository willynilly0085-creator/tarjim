"""The translator picker next to Translate never saves a translator that cannot work now, and the
line above Translate says when the saved one stopped working."""
from pathlib import Path
from typing import Any

import pytest

from tarjim import config
from tarjim.engines import local_servers
from tarjim.server import connections, translator_check


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(connections, "overview", lambda: {"api": []})
    return tmp_path


class Page(connections.ConnectionRoutes):
    def __init__(self, body: dict[str, Any]) -> None:
        self.body, self.answer = body, (0, None)

    def read_json(self) -> dict[str, Any]:
        return self.body

    def reply(self, code: int, payload: Any) -> None:
        self.answer = (code, payload)


def use(body: dict[str, Any]) -> tuple[int, Any]:
    page = Page(body)
    page.use_connection({})
    return page.answer


def running(monkeypatch: pytest.MonkeyPatch, models: list[str]) -> None:
    monkeypatch.setattr(local_servers, "alive", lambda _server, _url: True)
    monkeypatch.setattr(local_servers, "models_of", lambda _server, _url: models)


def test_a_local_program_without_models_is_refused(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    running(monkeypatch, [])
    code, payload = use({"provider": "local", "server": "ollama", "listen": "local"})
    assert code == 400 and payload["error"] == "unusable"
    assert config.setting("translate_provider") == ""


def test_a_local_program_with_a_model_is_saved(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    running(monkeypatch, ["qwen3:8b"])
    code, payload = use({"provider": "local", "server": "ollama", "model": "qwen3:8b",
                         "listen": "local"})
    assert code == 200 and "error" not in payload
    assert config.setting("translate_provider") == "local"


def test_a_key_provider_without_its_key_is_refused(home: Path) -> None:
    code, payload = use({"provider": "deepseek", "listen": "local"})
    assert code == 400 and payload["error"] == "unusable"
    config.save("deepseek_api_key", "sk-1234567890abcdefgh")
    assert use({"provider": "deepseek", "listen": "local"})[0] == 200


def test_the_line_above_translate_says_when_the_saved_translator_stopped_working(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config.save("translate_provider", "deepseek")
    assert connections.current_view()["works"] is False
    config.save("deepseek_api_key", "sk-1234567890abcdefgh")
    assert connections.current_view()["works"] is True
    config.save("translate_provider", "local")
    monkeypatch.setattr(local_servers, "answering", lambda _url: False)
    assert translator_check.works_now("local") is False
