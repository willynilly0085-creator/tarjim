"""What the security read of 2026-10-10 found, kept from coming back."""
from pathlib import Path

import pytest

from tarjim import config
from tarjim.models import Cue
from tarjim.phone import links
from tarjim.render.srt import render_srt
from tarjim.server.pairing import Pairing
from tarjim.server.routes import GET_ROUTES
from tarjim.server.voice_routes import VoiceRoutes

EXTENSION = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    return tmp_path


class Voices(VoiceRoutes):
    def __init__(self, body: dict[str, str]) -> None:
        self.body, self.code = body, 0

    def read_json(self) -> dict[str, str]:
        return self.body

    def reply(self, code: int, payload: object) -> None:
        self.code = code


def test_a_voice_key_does_not_follow_a_new_address(home: Path) -> None:
    config.save("speech_preset", "openai")
    config.save("speech_api_key", "sk-secret")
    moved = {"preset": "custom", "url": "https://elsewhere.example/v1", "model": "m", "voices": "v"}
    Voices(moved).voices_speech({})
    assert config.setting("speech_base_url") == "https://elsewhere.example/v1"
    assert config.setting("speech_api_key") == ""


def test_asking_again_replaces_the_waiting_request_and_each_has_a_number() -> None:
    pairing = Pairing()
    first, second = pairing.ask(EXTENSION), pairing.ask(EXTENSION)
    assert first is not None and second is not None
    assert [r.id for r in pairing.pending()] == [second.id]
    assert len(second.code) == 4 and second.code.isdigit()


def test_no_link_can_start_a_job() -> None:
    assert not any(pattern.match("/translate") for pattern, _name in GET_ROUTES)


def test_subtitle_files_carry_no_drawing_commands() -> None:
    hostile = "{" + chr(92) + "an8}{" + chr(92) + "p1}hello <font size=200>there</font>"
    text = render_srt([Cue(0.0, 2.0, text=hostile)])
    assert "{" not in text and "<" not in text and "hello" in text and "there" in text


@pytest.mark.parametrize("url", ["//8.8.8.8/share/x.mp4", "ftp://8.8.8.8/x.mp4", "file:///c:/x.mp4"])
def test_only_web_links_count_as_links(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "addresses", lambda _host: ["8.8.8.8"])
    assert links.public(url) is False


def test_a_custom_key_does_not_follow_a_new_address(home: Path) -> None:
    from tarjim.server.connections import ConnectionRoutes

    class Routes(ConnectionRoutes):
        def read_json(self) -> dict[str, str]:
            return {"url": "https://elsewhere.example/v1"}

        def reply(self, code: int, payload: object) -> None:
            self.code = code

    config.save("custom_base_url", "https://api.example/v1")
    config.save("custom_api_key", "sk-secret")
    Routes().save_address({})
    assert config.setting("custom_api_key") == ""
