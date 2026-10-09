"""Cloud dubbing voices the person links with their own key: ElevenLabs, and any service that
speaks OpenAI's speech format. Keys are saved through /keys like every other key; here are the
choices that are not secret."""
import re
from typing import Any

from tarjim.config import save, setting

Query = dict[str, list[str]]
VOICE_ID = re.compile(r"^[\w-]{1,64}$")
ADDRESS = re.compile(r"^https?://[\w.-]+(:\d{1,5})?(/[\w./-]*)?$")
MODEL = re.compile(r"^[\w.:/@+-]{1,120}$")
NAMES = re.compile(r"^[\w .:@+-]{1,40}(,[\w .:@+-]{1,40}){0,19}$")


def view() -> dict[str, Any]:
    from tarjim.dub import eleven, speech

    key = setting("eleven_api_key")
    return {"eleven": {"has_key": bool(key), "voices": eleven.view(key),
                       "voice": setting("eleven_voice")},
            "speech": {"has_key": bool(setting("speech_api_key")), "url": speech.address(),
                       "model": speech.model(), "voices": ", ".join(speech.voice_names())}}


def speech_choice(data: dict[str, Any]) -> dict[str, str] | None:
    url = str(data.get("url", "")).strip().rstrip("/")
    model = str(data.get("model", "")).strip()
    names = ",".join(n.strip() for n in str(data.get("voices", "")).split(",") if n.strip())
    fits = ADDRESS.match(url) and MODEL.match(model) and NAMES.match(names)
    return {"speech_base_url": url, "speech_model": model, "speech_voices": names} if fits else None


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
