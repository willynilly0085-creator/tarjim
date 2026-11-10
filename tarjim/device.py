"""Run models on the graphics card when PyTorch can use it, otherwise on the processor.

A card that failed twice in a row in this run (tarjim/card.py) is left alone until the engine
starts again: on 2026-11-10 an engine that had run for hours failed five jobs with "CUDA out of
memory" while the card was nearly empty, and nothing inside the process could bring it back.
"""
import threading
from typing import Any

CARD_FAILED = threading.Event()


def card_present() -> bool:
    import torch

    return bool(torch.cuda.is_available())


def best_device() -> str:
    if CARD_FAILED.is_set():
        return "cpu"
    return "cuda:0" if card_present() else "cpu"


def precision(device: str, fast: Any) -> Any:
    import torch

    return fast if device.startswith("cuda") else torch.float32
