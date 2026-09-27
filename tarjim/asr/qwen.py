import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from tarjim.asr.base import Transcript
from tarjim.models import Word

ASR_MODEL = "Qwen/Qwen3-ASR-1.7B"
ALIGNER_MODEL = "Qwen/Qwen3-ForcedAligner-0.6B"
BATCH = 8
MAX_TOKENS = 2048
CORE = re.compile(r"\w+", re.UNICODE)


def keep_fast_tokenizer(repo: str, processor: Any) -> None:
    from huggingface_hub import snapshot_download

    backend = getattr(getattr(processor, "tokenizer", None), "backend_tokenizer", None)
    if backend is None:
        return
    try:
        target = Path(snapshot_download(repo, local_files_only=True)) / "tokenizer.json"
        if not target.exists():
            backend.save(str(target))
    except (OSError, ValueError):
        return


@lru_cache(maxsize=1)
def shared_engine() -> "QwenEngine":
    return QwenEngine()


class QwenEngine:
    def __init__(self, device: str | None = None) -> None:
        import torch
        from qwen_asr import Qwen3ASRModel

        from tarjim.device import best_device, precision

        device = device or best_device()
        options = {"dtype": precision(device, torch.bfloat16), "device_map": device}
        self.model = Qwen3ASRModel.from_pretrained(
            ASR_MODEL, forced_aligner=ALIGNER_MODEL, forced_aligner_kwargs=options,
            max_inference_batch_size=BATCH, max_new_tokens=MAX_TOKENS, **options,
        )
        keep_fast_tokenizer(ASR_MODEL, self.model.processor)
        keep_fast_tokenizer(ALIGNER_MODEL, getattr(self.model.forced_aligner, "processor", None))

    def transcribe(self, audio_path: str) -> Transcript:
        result = self.model.transcribe(audio=audio_path, return_time_stamps=True)[0]
        items = list(result.time_stamps or [])
        words = attach_punctuation(result.text, items)
        return Transcript(language=result.language, text=result.text, words=words)


def core(text: str) -> str:
    return "".join(CORE.findall(text)).lower()


def attach_punctuation(text: str, items: list[Any]) -> list[Word]:
    queue = list(items)
    words: list[Word] = []
    for token in text.split():
        target = core(token)
        if not target or not queue:
            continue
        first = last = queue.pop(0)
        merged = core(first.text)
        while merged != target and queue and len(merged) < len(target):
            last = queue.pop(0)
            merged += core(last.text)
        words.append(Word(token, float(first.start_time), float(last.end_time)))
    return words
