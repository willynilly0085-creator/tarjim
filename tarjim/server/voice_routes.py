"""Cloud dubbing voices the person links with their own key: Gemini, ElevenLabs, Fish Audio, the
services known by name that speak OpenAI's speech format, and any other such service. Keys are
saved through /keys like every other key; here are the choices that are not secret."""
import re
from typing import Any

from tarjim.config import save, setting

Query = dict[str, list[str]]
VOICE_ID = re.compile(r"^[\w-]{1,64}$")
ADDRESS = re.compile(r"^https?://[\w.-]+(:\d{1,5})?(/[\w./-]*)?$")
MODEL = re.compile(r"^[\w.:/@+-]{0,120}$")
NAMES = re.compile(r"^([\w .:@+-]{1,40}(,[\w .:@+-]{1,40}){0,29})?$")
KEYED = {"gemini": "gemini_api_key", "fish": "fish_api_key"}


def speech_view() -> dict[str, Any]:
    from tarjim.dub import speech

    known = [{"id": name, "name": found.name, "languages": found.languages, "keys": found.keys}
             for name, found in speech.SERVICES.items()]
    return {"has_key": bool(setting("speech_api_key")), "preset": speech.chosen(),
            "name": speech.service().name if speech.chosen() != speech.CUSTOM else "",
            "presets": known, "url": speech.service().address,
            "model": setting("speech_model"), "voices": setting("speech_voices")}


def view() -> dict[str, Any]:
    from tarjim.dub import eleven

    key = setting("eleven_api_key")
    keyed = {name: {"has_key": bool(setting(secret))} for name, secret in KEYED.items()}
    return {**keyed, "speech": speech_view(),
            "eleven": {"has_key": bool(key), "voices": eleven.view(key),
                       "voice": setting("eleven_voice")}}


def speech_choice(data: dict[str, Any]) -> dict[str, str] | None:
    """What to save for a speech service: a known one needs no address; another one does."""
    from tarjim.dub.speech import CUSTOM, SERVICES

    preset = str(data.get("preset") or CUSTOM)
    url = "" if preset in SERVICES else str(data.get("url", "")).strip().rstrip("/")
    model = str(data.get("model", "")).strip()
    names = ",".join(n.strip() for n in str(data.get("voices", "")).split(",") if n.strip())
    described = preset in SERVICES or bool(ADDRESS.match(url) and model and names)
    if preset not in (*SERVICES, CUSTOM) or not described:
        return None
    if not MODEL.match(model) or not NAMES.match(names):
        return None
    return {"speech_preset": preset, "speech_base_url": url, "speech_model": model,
            "speech_voices": names}


class VoiceRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def voices_state(self, _query: Query) -> None:
        self.reply(200, view())

    def voices_eleven(self, _query: Query) -> None:
        voice = str(self.read_json().get("voice", ""))
        if voice and not VOICE_ID.match(voice):
            return self.reply(400, {"error": "voice"})
        save("eleven_voice", voice)
        self.reply(200, view())

    def voices_speech(self, _query: Query) -> None:
        chosen = speech_choice(self.read_json())
        if chosen is None:
            return self.reply(400, {"error": "speech"})
        for name, value in chosen.items():
            save(name, value)
        self.reply(200, view())
