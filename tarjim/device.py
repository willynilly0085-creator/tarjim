"""Run models on the graphics card when PyTorch can use it, otherwise on the processor.

The card is an Nvidia card through CUDA or, on a Mac with an Apple chip, the chip's own graphics
through Metal ("mps"). An operation Metal lacks runs on the processor by itself
(PYTORCH_ENABLE_MPS_FALLBACK, set in tarjim/__init__.py before PyTorch loads), so a model never
fails for that.

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


def apple_present() -> bool:
    import torch

    metal = getattr(torch.backends, "mps", None)
    return bool(metal is not None and metal.is_available())


def best_device() -> str:
    if CARD_FAILED.is_set():
        return "cpu"
    if card_present():
        return "cuda:0"
    return "mps" if apple_present() else "cpu"


def precision(device: str, fast: Any) -> Any:
    import torch

    return fast if device.startswith("cuda") else torch.float32
