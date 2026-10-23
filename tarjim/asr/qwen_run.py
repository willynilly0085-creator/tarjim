"""Hearing and timing with Transformers' own Qwen3-ASR classes, the way the qwen-asr package did.

Recognition: each piece gets the model's own prompt (an empty system turn, the sound, then the
assistant's turn), 2048 new tokens at most, greedy, several pieces at a time: as many as the
memory left beside the models holds (each three-minute piece takes about 1.3 GB on the graphics
card in bfloat16, twice that on the processor), one at the least and eight at the most. The model
names the language itself ("language English<asr_text>..."). Timing: the forced aligner takes
the sound with the words heard, each followed by two timestamp marks, and returns the start and
end of every word. Transformers' helper for that refuses languages outside the eleven its card
lists, while qwen-asr aligned every language (Arabic among them) by its words, so the input is
built here as qwen-asr built it; Japanese and Korean are split into words as both libraries do.
"""
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np

BATCH = 8
PIECE_GB = {"cuda": 1.4, "cpu": 2.8}
SPARE_GB = 1.0
GIB = 2**30
MAX_TOKENS = 2048
RATE = 16000
PROMPT = ("<|im_start|>system\n<|im_end|>\n<|im_start|>user\n<|audio_start|><|audio_pad|>"
          "<|audio_end|><|im_end|>\n<|im_start|>assistant\n")
MARKS = "<timestamp><timestamp>"
OWN_SPLIT = ("Japanese", "Korean")


@dataclass(frozen=True)
class Stamp:
    text: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class Loaded:
    model: Any
    processor: Any


def free_gb(device: Any) -> float:
    import psutil
    import torch

    if device.type != "cuda":
        return float(psutil.virtual_memory().available) / GIB
    torch.cuda.empty_cache()  # what PyTorch keeps aside may be in pieces too small to use
    free, _total = torch.cuda.mem_get_info(device)
    return float(free) / GIB


def batch_size(loaded: Loaded) -> int:
    device = loaded.model.device
    room = free_gb(device) - SPARE_GB
    return max(1, min(BATCH, int(room // PIECE_GB["cuda" if device.type == "cuda" else "cpu"])))


def batches(items: list[Any], size: int) -> Iterator[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def inputs_for(loaded: Loaded, texts: list[str], wavs: list[np.ndarray]) -> Any:
    found = loaded.processor(text=texts, audio=wavs, sampling_rate=RATE, return_tensors="pt",
                             padding=True)
    return found.to(loaded.model.device).to(loaded.model.dtype)


def parsed(processor: Any, raw: str) -> tuple[str, str]:
    """(language, text); the language as qwen-asr wrote it, empty when the piece was silent."""
    found = processor.parse_output(raw)
    language = str(found["language"] or "").strip()
    return language[:1].upper() + language[1:].lower(), str(found["transcription"]).strip()


def recognise(loaded: Loaded, wavs: list[np.ndarray]) -> list[tuple[str, str]]:
    import torch

    heard: list[tuple[str, str]] = []
    for group in batches(wavs, batch_size(loaded)):
        inputs = inputs_for(loaded, [PROMPT] * len(group), group)
        with torch.inference_mode():
            out = loaded.model.generate(**inputs, max_new_tokens=MAX_TOKENS, do_sample=False)
        new = out[:, inputs["input_ids"].shape[1]:]
        raw = loaded.processor.batch_decode(new, skip_special_tokens=True,
                                            clean_up_tokenization_spaces=False)
        heard.extend(parsed(loaded.processor, text) for text in raw)
    return heard


def words_of(processor: Any, text: str, language: str) -> list[str]:
    own = language if language in OWN_SPLIT else None
    return list(processor.split_words_for_alignment(text, own))


def align(loaded: Loaded, wavs: list[np.ndarray],
          heard: list[tuple[str, str]]) -> list[list[Stamp]]:
    import torch

    stamps: list[list[Stamp]] = []
    for group in batches(list(zip(wavs, heard, strict=True)), batch_size(loaded)):
        words = [words_of(loaded.processor, text, language) for _, (language, text) in group]
        texts = ["<|audio_start|><|audio_pad|><|audio_end|>" + MARKS.join(w) + MARKS for w in words]
        inputs = inputs_for(loaded, texts, [wav for wav, _ in group])
        with torch.inference_mode():
            logits = loaded.model(**inputs).logits
        found = loaded.processor.decode_forced_alignment(
            logits=logits, input_ids=inputs["input_ids"], word_lists=words,
            timestamp_token_id=loaded.model.config.timestamp_token_id)
        stamps.extend([Stamp(**item) for item in items] for items in found)
    return stamps
