"""Local listening: Qwen3-ASR-1.7B hears the words and the language, Qwen3-ForcedAligner-0.6B
times each word, both through Transformers' own classes (tarjim/asr/qwen_load.py), in bfloat16
on the graphics card or float32 on the processor. Long sound is heard in three-minute pieces."""
import re
from dataclasses import replace
from functools import lru_cache
from typing import Any

import numpy as np

from tarjim.asr.base import Transcript
from tarjim.asr.pieces import RATE, Piece, pieces
from tarjim.asr.qwen_load import ALIGNER_MODEL, ASR_MODEL, EARLIER_ALIGNER, EARLIER_ASR
from tarjim.asr.qwen_run import BATCH, MAX_TOKENS, Stamp, align, recognise
from tarjim.models import Word
from tarjim.scripts import split_words

__all__ = ["ALIGNER_MODEL", "ASR_MODEL", "BATCH", "EARLIER_ALIGNER", "EARLIER_ASR",
           "MAX_TOKENS", "QwenEngine", "shared_engine"]
CORE = re.compile(r"\w+", re.UNICODE)


@lru_cache(maxsize=1)
def shared_engine() -> "QwenEngine":
    return QwenEngine()


def read_sound(path: str) -> np.ndarray:
    """Mono 16 kHz in [-1, 1], as qwen-asr read it; tarjim's own wav is already that."""
    import soundfile

    wav, rate = soundfile.read(path, dtype="float32", always_2d=True)
    mono = wav.mean(axis=1)
    if rate != RATE and len(mono):
        times = np.arange(0, len(mono) / rate, 1 / RATE)
        mono = np.interp(times, np.arange(len(mono)) / rate, mono).astype(np.float32)
    peak = float(np.max(np.abs(mono))) if len(mono) else 0.0
    scaled: np.ndarray = np.clip(mono / peak if peak > 1.0 else mono, -1.0, 1.0)
    return scaled.astype(np.float32)


def languages(found: list[str]) -> str:
    """The languages of the pieces in order, each once in a row ("English,Arabic")."""
    merged: list[str] = []
    for language in found:
        if language and (not merged or merged[-1] != language):
            merged.append(language)
    return ",".join(merged)


def shifted(stamps: list[Stamp], piece: Piece) -> list[Stamp]:
    at = piece.offset
    return [Stamp(s.text, round(s.start_time + at, 3), round(s.end_time + at, 3)) for s in stamps]


class QwenEngine:
    def __init__(self, device: str | None = None) -> None:
        from tarjim.asr.qwen_load import load_pair
        from tarjim.device import best_device

        self.asr, self.aligner = load_pair(device or best_device())

    def transcribe(self, audio_path: str) -> Transcript:
        parts = pieces(read_sound(audio_path))
        heard = recognise(self.asr, [part.wav for part in parts])
        spoken = [k for k, (_, text) in enumerate(heard) if text]
        timed = align(self.aligner, [parts[k].wav for k in spoken], [heard[k] for k in spoken])
        pairs = zip(spoken, timed, strict=True)
        stamps = [s for k, found in pairs for s in shifted(found, parts[k])]
        text = " ".join(text for _, text in heard if text)
        language = languages([language for language, _ in heard])
        return Transcript(language=language, text=text, words=attach_punctuation(text, stamps))


def core(text: str) -> str:
    return "".join(CORE.findall(text)).lower()


def letters(text: str) -> int:
    return sum(len(part) for part in CORE.findall(text))


def attach_punctuation(text: str, items: list[Any]) -> list[Word]:
    """The heard text's own words and punctuation, timed by the aligner's pieces: letter by
    letter, so a word the aligner split ("it", "s") or several it joined come out right."""
    timeline = [(float(i.start_time), float(i.end_time))
                for i in items for _ in range(letters(i.text))]
    words: list[Word] = []
    cursor = 0
    for token in split_words(text):
        size = letters(token)
        if not size and words:  # "Vraiment ?": the mark ends the word before it
            words[-1] = replace(words[-1], text=f"{words[-1].text} {token}")
        if not size or cursor >= len(timeline):
            continue
        span = timeline[cursor:cursor + size]
        words.append(Word(token, span[0][0], span[-1][1]))
        cursor += size
    return words
