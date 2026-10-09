"""Dub with ElevenLabs: ready voices from the person's own library, a different one per speaker, or
each speaker's own voice cloned for this job and deleted from ElevenLabs when the job ends.

Follows the API reference as read on 2026-10-09. The sound is asked for as MP3, which every plan
may have; 44.1 kHz PCM needs the Pro plan. Cloning needs a paid plan: ElevenLabs refuses it
otherwise, and its refusal is shown as it is.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.dub.cast import VoiceError, ask, assign, sound
from tarjim.dub.lines import Line

API = "https://api.elevenlabs.io"
NAME = "ElevenLabs"
MODEL = "eleven_multilingual_v2"
FORMAT = "mp3_44100_128"
PARALLEL = 3
PAGE = 100


def headers(key: str) -> dict[str, str]:
    return {"xi-api-key": key}


def library(key: str) -> list[dict[str, str]]:
    """The voices in the person's ElevenLabs library, in the order ElevenLabs gives them."""
    reply = ask(NAME, "GET", f"{API}/v2/voices", headers=headers(key), params={"page_size": PAGE})
    rows = reply.json().get("voices", [])
    return [{"id": str(row["voice_id"]), "name": str(row.get("name") or row["voice_id"])}
            for row in rows if isinstance(row, dict) and row.get("voice_id")]


class ElevenVoices:
    def __init__(self, key: str, references: dict[str, Path], clone: bool = False,
                 preferred: str = "") -> None:
        self.key = key
        self.owned: list[str] = []
        if not clone:
            ready = [voice["id"] for voice in library(key)]
            self.voices = assign(sorted(references), ready, preferred)
            return
        try:
            self.voices = {speaker: self.upload(path) for speaker, path in references.items()}
        except Exception:
            self.close()
            raise

    def upload(self, reference: Path) -> str:
        with reference.open("rb") as sample:
            reply = ask(NAME, "POST", f"{API}/v1/voices/add", headers=headers(self.key),
                        data={"name": "tarjim-temporary"},
                        files={"files": (reference.name, sample, "audio/wav")})
        voice = str(reply.json()["voice_id"])
        self.owned.append(voice)
        return voice

    def speak(self, line: Line) -> np.ndarray:
        voice = self.voices.get(line.speaker) or next(iter(self.voices.values()))
        reply = ask(NAME, "POST", f"{API}/v1/text-to-speech/{voice}", headers=headers(self.key),
                    params={"output_format": FORMAT}, json={"text": line.text, "model_id": MODEL})
        return sound(reply)

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        try:
            with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
                return list(pool.map(self.speak, lines))
        finally:
            self.close()

    def close(self) -> None:
        for voice in self.owned:
            try:
                ask(NAME, "DELETE", f"{API}/v1/voices/{voice}", headers=headers(self.key))
            except VoiceError:
                continue
        self.owned.clear()


def works(key: str) -> bool:
    try:
        library(key)
    except (VoiceError, ValueError, KeyError):
        return False
    return True


def view(key: str) -> list[dict[str, Any]]:
    try:
        return list(library(key)) if key else []
    except (VoiceError, ValueError, KeyError):
        return []
