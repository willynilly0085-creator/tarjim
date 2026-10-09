"""Dub with a voice service that speaks OpenAI's speech format (`POST <address>/audio/speech`).

Services known by name come ready: their address, the model and voices for the language being
dubbed, the sound format they return and how much text they take at once, all as their own
documentation gave them on 2026-10-09. Any other service is described by the person: address,
model and voice names. Each speaker gets a different voice, and only the text of each line is sent.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np

from tarjim.config import setting
from tarjim.dub.cast import VoiceError, ask, assign, sound
from tarjim.dub.lines import Line

PARALLEL = 3
CUSTOM = "custom"
ANY = "*"
OPENAI_VOICES = "alloy,ash,coral,echo,fable,nova,onyx,sage,shimmer"
Offer = tuple[str, str]


@dataclass(frozen=True)
class Service:
    name: str
    address: str
    offers: dict[str, Offer] = field(default_factory=dict)
    sound: str = "mp3"
    most: int = 0
    keys: str = ""

    @property
    def languages(self) -> list[str]:
        return [] if ANY in self.offers else sorted(self.offers)


SERVICES = {
    "openai": Service("OpenAI", "https://api.openai.com/v1",
                      {ANY: ("gpt-4o-mini-tts", OPENAI_VOICES)},
                      keys="https://platform.openai.com/api-keys"),
    "groq": Service("Groq", "https://api.groq.com/openai/v1", {
        "ar": ("canopylabs/orpheus-arabic-saudi", "abdullah,noura,fahad,lulwa,sultan,aisha"),
        "en": ("canopylabs/orpheus-v1-english", "troy,hannah,austin,diana,daniel,autumn")},
        sound="wav", most=200, keys="https://console.groq.com/keys"),
    "openrouter": Service("OpenRouter", "https://openrouter.ai/api/v1",
                          {ANY: ("openai/gpt-4o-mini-tts-2025-12-15", OPENAI_VOICES)},
                          keys="https://openrouter.ai/settings/keys"),
    "together": Service("Together AI", "https://api.together.ai/v1", {
        "en": ("canopylabs/orpheus-3b-0.1-ft", "tara,leo,leah,dan,jess,zac,mia,zoe")},
        keys="https://api.together.ai/settings/api-keys"),
}


def chosen() -> str:
    picked = setting("speech_preset")
    return picked if picked in SERVICES else CUSTOM


def service() -> Service:
    """The service in use: one known by name, or the address the person gave."""
    return SERVICES.get(chosen()) or Service(
        "voice service", setting("speech_base_url").rstrip("/"))


def offer(language: str) -> Offer:
    """The model and voice names for a language: the person's own first, then the service's."""
    ready = service().offers
    model, names = ready.get(language) or ready.get(ANY) or ("", "")
    return setting("speech_model") or model, setting("speech_voices") or names


def pieces(text: str, most: int) -> list[str]:
    """A line cut at spaces into parts the service accepts; whole when it has no limit."""
    parts: list[str] = [""]
    for word in text.split():
        joined = f"{parts[-1]} {word}".strip()
        if most and len(joined) > most and parts[-1]:
            parts.append(word)
        else:
            parts[-1] = joined
    return [part for part in parts if part]


class SpeechVoices:
    def __init__(self, speakers: list[str], language: str) -> None:
        self.service = service()
        self.model, names = offer(language)
        if not self.service.address or not self.model or not names:
            raise VoiceError(f"{self.service.name}: no voice for language {language}; give its "
                             "address, model and voice names in tarjim's settings")
        self.voices = assign(speakers, [name.strip() for name in names.split(",")])

    def say(self, text: str, voice: str) -> np.ndarray:
        reply = ask(self.service.name, "POST", f"{self.service.address}/audio/speech",
                    headers={"Authorization": f"Bearer {setting('speech_api_key')}"},
                    json={"model": self.model, "input": text, "voice": voice,
                          "response_format": self.service.sound})
        return sound(reply)

    def speak(self, line: Line) -> np.ndarray:
        voice = self.voices.get(line.speaker) or next(iter(self.voices.values()))
        said = [self.say(part, voice) for part in pieces(line.text, self.service.most)]
        return np.concatenate(said) if said else np.zeros(0, dtype=np.float32)

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
            return list(pool.map(self.speak, lines))
