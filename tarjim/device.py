"""Run models on the graphics card when PyTorch can use it, otherwise on the processor."""
from typing import Any


def best_device() -> str:
    import torch

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def precision(device: str, fast: Any) -> Any:
    import torch

    return fast if device.startswith("cuda") else torch.float32
