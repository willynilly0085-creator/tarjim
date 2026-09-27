"""Natural dubbing voices from Gemini TTS: one voice per speaker, matched to the speaker's pitch.

Each speaker's lines go in one request (the free tier allows few requests a day), and the
word aligner cuts the recording back into lines.
"""
import base64
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.config import setting
from tarjim.dub.audio import RATE, decode
from tarjim.dub.lines import Line
from tarjim.dub.split import split_lines

MODELS = ("gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts")
LOW_VOICES = ("Charon", "Orus", "Fenrir", "Iapetus", "Algenib", "Schedar")
HIGH_VOICES = ("Kore", "Leda", "Aoede", "Despina", "Sulafat", "Achernar")
LOW_PITCH_HZ = 165.0
PITCH_RANGE = (60.0, 400.0)
BATCH_CHARS = 2500
REQUEST_MS = 180_000
BUSY = 503
ACCENTS = {"saudi": "a natural Saudi Arabic accent", "msa": "clear Modern Standard Arabic"}


class VoiceUnavailable(RuntimeError):
    pass


def pitch_of(reference: Path) -> float:
    import librosa

    samples = decode(reference)
    if samples.size < RATE:
        return 0.0
    low, high = PITCH_RANGE
    track = librosa.yin(samples, fmin=low, fmax=high, sr=RATE)
    voiced = track[(track > low) & (track < high)]
    return float(np.median(voiced)) if voiced.size else 0.0


def cast(references: dict[str, Path]) -> dict[str, str]:
    voices: dict[str, str] = {}
    used = {"low": 0, "high": 0}
    for speaker, path in sorted(references.items()):
        band = "high" if pitch_of(path) > LOW_PITCH_HZ else "low"
        pool = HIGH_VOICES if band == "high" else LOW_VOICES
        voices[speaker] = pool[used[band] % len(pool)]
        used[band] += 1
    return voices


def style_for(language: str, dialect: str) -> str:
    accent = ACCENTS.get(dialect, "") if language == "ar" else ""
    tone = ("natural and expressive, like a professional voice actor dubbing a video; "
            "a short pause after each line")
    return f"{tone}; {accent}" if accent else tone


def batches(lines: list[Line]) -> list[list[int]]:
    groups: dict[str, list[list[int]]] = {}
    for index, line in enumerate(lines):
        chunks = groups.setdefault(line.speaker, [[]])
        if sum(len(lines[i].text) for i in chunks[-1]) + len(line.text) > BATCH_CHARS:
            chunks.append([])
        chunks[-1].append(index)
    return [chunk for chunks in groups.values() for chunk in chunks if chunk]


class GeminiVoices:
    def __init__(self, references: dict[str, Path], language: str, dialect: str = "saudi") -> None:
        from google import genai
        from google.genai import types

        options = types.HttpOptions(timeout=REQUEST_MS,
                                    retry_options=types.HttpRetryOptions(
                                        attempts=1, http_status_codes=[BUSY]))
        self.client: Any = genai.Client(api_key=setting("gemini_api_key"), http_options=options)
        self.voices = cast(references) or {"": LOW_VOICES[0]}
        self.language = language
        self.style = style_for(language, dialect)

    def request(self, model: str, text: str, voice: str) -> np.ndarray:
        content = {"type": "text", "text": text,
                   "annotations": [{"type": "speech_metadata", "style": self.style}]}
        answer = self.client.interactions.create(
            model=model, input=[{"type": "user_input", "content": [content]}],
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]})
        return decode(base64.b64decode(answer.output_audio.data))

    def record(self, text: str, voice: str) -> np.ndarray:
        problems = []
        for model in MODELS:
            try:
                return self.request(model, text, voice)
            except Exception as error:
                problems.append(f"{model}: {str(error)[:160]}")
        raise VoiceUnavailable("; ".join(problems))

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        speech = [np.zeros(0, dtype=np.float32) for _ in lines]
        for chunk in batches(lines):
            texts = [lines[i].text for i in chunk]
            voice = self.voices.get(lines[chunk[0]].speaker) or next(iter(self.voices.values()))
            pieces = split_lines(self.record("\n\n".join(texts), voice), texts, self.language)
            if len(pieces) != len(chunk):
                raise VoiceUnavailable("could not cut the recording back into lines")
            for index, piece in zip(chunk, pieces, strict=True):
                speech[index] = piece
        return speech
