"""Dub with any voice service that speaks OpenAI's speech format (`POST <address>/audio/speech`):
OpenAI itself, or another provider the person points tarjim at. The person gives the address, a
key, the model and the names of the voices; each speaker gets a different one. Only the text of
each line is sent.
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from tarjim.config import setting
from tarjim.dub.cast import VoiceError, ask, assign, sound
from tarjim.dub.lines import Line

NAME = "voice service"
OPENAI = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini-tts"
OPENAI_VOICES = ("alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer")
PARALLEL = 3


def address() -> str:
    return (setting("speech_base_url") or OPENAI).rstrip("/")


def model() -> str:
    return setting("speech_model") or (OPENAI_MODEL if address() == OPENAI else "")


def voice_names() -> list[str]:
    named = [name.strip() for name in setting("speech_voices").split(",") if name.strip()]
    return named or (list(OPENAI_VOICES) if address() == OPENAI else [])


class SpeechVoices:
    def __init__(self, speakers: list[str]) -> None:
        if not model() or not voice_names():
            raise VoiceError("voice service: set its model and at least one voice name first")
        self.voices = assign(speakers, voice_names())

    def speak(self, line: Line) -> np.ndarray:
        voice = self.voices.get(line.speaker) or next(iter(self.voices.values()))
        reply = ask(NAME, "POST", f"{address()}/audio/speech",
                    headers={"Authorization": f"Bearer {setting('speech_api_key')}"},
                    json={"model": model(), "input": line.text, "voice": voice,
                          "response_format": "mp3"})
        return sound(reply)

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
            return list(pool.map(self.speak, lines))
