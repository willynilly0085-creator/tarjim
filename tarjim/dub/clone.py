import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.dub.audio import RATE, resample, trim
from tarjim.dub.lines import Line

LANGUAGES = {"ar", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "zh", "ja",
             "hu", "ko", "hi"}
XTTS_RATE = 24000
LIMIT = 160
TEMPERATURE = 0.5
ATTEMPTS = 3
BASE_SECONDS = 0.9
CHARS_PER_SECOND = 7.0
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


@lru_cache(maxsize=1)
def voice_model(device: str) -> Any:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts

    from tarjim.tools import voice_folder

    folder = voice_folder()
    config = XttsConfig()
    config.load_json(str(folder / "config.json"))
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir=str(folder), use_deepspeed=False)
    model.to(device)
    model.eval()
    return model


class CloneVoices:
    def __init__(self, references: dict[str, Path], language: str) -> None:
        import torch

        self.model: Any = voice_model("cuda" if torch.cuda.is_available() else "cpu")
        self.language = "zh-cn" if language == "zh" else language
        self.latents = {speaker: self.model.get_conditioning_latents(audio_path=[str(path)])
                        for speaker, path in references.items()}

    def once(self, line: Line) -> np.ndarray:
        latent, embedding = self.latents.get(line.speaker) or next(iter(self.latents.values()))
        parts = [self.model.inference(part, self.language, latent, embedding,
                                      temperature=TEMPERATURE)["wav"]
                 for part in split_for_tts(line.text)]
        wav = np.concatenate([np.asarray(p, dtype=np.float32) for p in parts])
        return trim(resample(wav, XTTS_RATE))

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
