"""Dub in each speaker's own voice with VoxCPM2 (Apache-2.0), on this computer.

Only the reference audio is given, not its transcript, so the model copies the timbre, not the
accent: an English speaker is heard speaking natural Arabic, not Arabic with an English accent.
Chosen after a blind listening test by a native Saudi speaker against XTTS v2 and Chatterbox.
"""
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.dub.audio import RATE, resample, trim
from tarjim.dub.lines import Line

REPO = "openbmb/VoxCPM2"
PACKAGE = "voxcpm==2.0.3"
LANGUAGES = {"ar", "en", "zh", "da", "nl", "fi", "fr", "de", "el", "he", "hi", "id", "it", "ja",
             "ko", "ms", "no", "pl", "pt", "ru", "es", "sw", "sv", "tl", "th", "tr", "vi"}
STEPS = 10
GUIDANCE = 2.0
LIMIT = 220
ATTEMPTS = 2
BASE_SECONDS = 1.5
CHARS_PER_SECOND = 6.0
SENTENCE = re.compile(r"(?<=[.!?،؛,;؟])\s+")


def split_for_tts(text: str, limit: int = LIMIT) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for piece in SENTENCE.split(text):
        for word in piece.split():
            if current and len(current) + 1 + len(word) > limit:
                parts.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
    return [*parts, current] if current else parts


def plausible(text: str) -> float:
    return BASE_SECONDS + len(text.strip()) / CHARS_PER_SECOND


def load(optimize: bool) -> Any:
    from voxcpm import VoxCPM

    return VoxCPM.from_pretrained(REPO, load_denoiser=False, local_files_only=True,
                                  optimize=optimize)


@lru_cache(maxsize=1)
def voice_model() -> Any:
    from tarjim.memory import free_for_voice

    free_for_voice()
    try:
        return load(optimize=True)
    except RuntimeError:
        return load(optimize=False)


class CloneVoices:
    def __init__(self, references: dict[str, Path], language: str) -> None:
        self.model: Any = voice_model()
        self.rate = int(self.model.tts_model.sample_rate)
        self.references = {speaker: str(path) for speaker, path in references.items()}
        self.language = language

    def once(self, line: Line) -> np.ndarray:
        reference = self.references.get(line.speaker) or next(iter(self.references.values()))
        parts = [self.model.generate(text=part, reference_wav_path=reference, cfg_value=GUIDANCE,
                                     inference_timesteps=STEPS)
                 for part in split_for_tts(line.text)]
        wav = np.concatenate([np.asarray(p, dtype=np.float32) for p in parts])
        return trim(resample(wav, self.rate))

    def speak(self, line: Line) -> np.ndarray:
        takes = []
        for _ in range(ATTEMPTS):
            wav = self.once(line)
            if wav.size / RATE <= plausible(line.text):
                return wav
            takes.append(wav)
        return min(takes, key=lambda w: w.size)

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        return [self.speak(line) for line in lines]
