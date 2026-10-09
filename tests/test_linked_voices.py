"""Dubbing through a voice service the person links with their own key: ElevenLabs, or any service
that speaks OpenAI's speech format."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import requests

from tarjim import config, keys
from tarjim.dub import cast, eleven, make, speech
from tarjim.dub.lines import Line
from tarjim.phone import choice
from tarjim.server import voice_routes
from tarjim.server.jobs import DUBBING, MODES, classify

LINES = [Line(0.0, 1.0, "S1", "مرحبا", "hi"), Line(1.0, 2.0, "S2", "أهلين", "hey")]
LIBRARY = {"voices": [{"voice_id": "v-one", "name": "Sara"}, {"voice_id": "v-two", "name": "Omar"},
                      {"voice_id": "v-three", "name": "Lina"}]}


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(cast, "decode", lambda _sound: np.ones(4, dtype=np.float32))


class Service:
    """A voice service that records what it was asked and answers like the real one."""

    def __init__(self, refuse: dict[str, tuple[int, Any]] | None = None) -> None:
        self.asked: list[tuple[str, str, dict[str, Any]]] = []
        self.refuse = refuse or {}

    def request(self, method: str, url: str, **options: Any) -> Any:
        self.asked.append((method, url, options))
        for part, (status, body) in self.refuse.items():
            if part in url:
                return SimpleNamespace(status_code=status, json=lambda body=body: body, text="")
        body = LIBRARY if url.endswith("/voices") else {"voice_id": f"clone-{len(self.asked)}"}
        return SimpleNamespace(status_code=200, json=lambda: body, content=b"mp3")


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> Service:
    made = Service()
    monkeypatch.setattr(requests, "request", made.request)
    return made


def spoken_with(service: Service) -> list[str]:
    return [url.rsplit("/", 1)[-1] for method, url, _options in service.asked
            if method == "POST" and "text-to-speech" in url]


def test_each_speaker_gets_a_different_ready_voice_and_the_preferred_one_leads(
        service: Service) -> None:
    voices = eleven.ElevenVoices("key", {"S1": Path("a.wav"), "S2": Path("b.wav")},
                                 preferred="v-two")
    assert len(voices.speak_all(LINES)) == 2 and voices.voices == {"S1": "v-two", "S2": "v-one"}
    assert sorted(spoken_with(service)) == ["v-one", "v-two"]
    sent = next(o for m, u, o in service.asked if u.endswith("/text-to-speech/v-two"))
    assert sent["headers"] == {"xi-api-key": "key"} and sent["json"]["text"] == "مرحبا"
    assert cast.assign(["a", "b", "c"], ["x", "y"]) == {"a": "x", "b": "y", "c": "x"}


def test_a_cloned_voice_is_deleted_when_the_job_ends_even_if_it_fails(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "S1.wav"
    sample.write_bytes(b"wav")
    service = Service({"text-to-speech": (402, {"detail": {
        "status": "quota_exceeded", "message": "You have 3 credits left"}})})
    monkeypatch.setattr(requests, "request", service.request)
    voices = eleven.ElevenVoices("key", {"S1": sample}, clone=True)
    with pytest.raises(cast.VoiceError, match="ElevenLabs 402: You have 3 credits left") as caught:
        voices.speak_all(LINES[:1])
    assert [m for m, u, _o in service.asked if "/v1/voices/" in u] == ["POST", "DELETE"]
    assert classify(caught.value) == "dub"


def test_any_service_in_openais_speech_format_can_dub(service: Service) -> None:
    config.save("speech_api_key", "sk-speech-key-000000")
    assert voice_routes.speech_choice({"url": "ftp://x", "model": "m", "voices": "a"}) is None
    assert voice_routes.speech_choice({"preset": "nobody"}) is None
    chosen = voice_routes.speech_choice({"url": "https://voices.example/v1/", "model": "tts-2",
                                         "voices": "nova, sage"})
    assert chosen is not None and chosen["speech_preset"] == "custom"
    for name, value in chosen.items():
        config.save(name, value)
    speech.SpeechVoices(["S1", "S2"], "ar").speak_all(LINES)
    sent = [o for _m, u, o in service.asked if u == "https://voices.example/v1/audio/speech"]
    assert {o["json"]["input"]: o["json"]["voice"] for o in sent} == {
        "مرحبا": "nova", "أهلين": "sage"}
    assert sent[0]["json"]["model"] == "tts-2" and "Bearer sk-speech" in str(sent[0]["headers"])


def use(preset: str) -> None:
    chosen = voice_routes.speech_choice({"preset": preset})
    assert chosen is not None
    for name, value in chosen.items():
        config.save(name, value)


def test_a_service_known_by_name_brings_its_model_and_voices_for_the_language(
        service: Service) -> None:
    use("groq")
    assert speech.offer("ar")[0] == "canopylabs/orpheus-arabic-saudi"
    assert speech.offer("en")[1].startswith("troy")
    with pytest.raises(cast.VoiceError, match="Groq: no voice for language fr"):
        speech.SpeechVoices(["S1"], "fr")
    long_line = Line(0.0, 9.0, "S1", " ".join(["كلمة"] * 80), "words")
    speech.SpeechVoices(["S1"], "ar").speak_all([long_line])
    sent = [o["json"] for _m, u, o in service.asked if u.endswith("/openai/v1/audio/speech")]
    assert len(sent) > 1 and all(len(body["input"]) <= 200 for body in sent)
    assert {body["voice"] for body in sent} == {"abdullah"} and sent[0]["response_format"] == "wav"
    assert " ".join(body["input"] for body in sent) == long_line.text
    use("openai")
    assert speech.offer("ja") == ("gpt-4o-mini-tts", speech.OPENAI_VOICES)
    listed = {p["id"]: p["languages"] for p in voice_routes.view()["speech"]["presets"]}
    assert listed["groq"] == ["ar", "en"] and listed["openai"] == [] and "openrouter" in listed


def test_a_linked_voice_without_its_key_says_so_and_is_never_swapped(
        monkeypatch: pytest.MonkeyPatch) -> None:
    for engine in ("eleven", "eleven:clone", "speech"):
        with pytest.raises(make.DubUnavailable, match="API key missing") as caught:
            make.choose(engine, "ar")
        assert classify(caught.value) == "key"
    config.save("eleven_api_key", "e" * 32)
    assert make.choose("eleven:clone", "ur") == "eleven"
    assert {"dub-eleven", "dub-elevenclone", "dub-speech"} <= set(DUBBING) <= set(MODES)


def test_the_key_is_checked_before_it_is_saved_and_the_phone_offers_the_voice_after(
        service: Service) -> None:
    assert "dub-eleven" not in choice.offered() and "dub-eleven" in choice.MODES
    assert keys.store("eleven", "e" * 32) == "saved"
    assert service.asked[0][1].endswith("/v2/voices")
    assert choice.offered()[-2:] == ["dub-eleven", "dub-elevenclone"]
    assert voice_routes.view()["eleven"]["voices"][0] == {"id": "v-one", "name": "Sara"}
