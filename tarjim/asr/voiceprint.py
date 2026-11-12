"""Whose voice a stretch of sound is: a voice print, 256 numbers that are close for one voice.

WeSpeaker's ResNet34 (trained on VoxCeleb, CC-BY-4.0) is one 26 MB ONNX file run by onnxruntime: on
the graphics card when tarjim uses one (measured 2026-11-12 on a 7-minute clip, 139 windows: 0.2 s
against 1.6 s on the processor), otherwise on the processor, a few hundredths of a second a line,
so it runs on any computer. A card that will not take it is no reason to fail: the processor
answers instead, for that line and from then on. It comes with the
timing tool; a computer that set tarjim up before it existed fetches it the first time it is
needed, and until then, or when it cannot be fetched, the listener's labels stand as they are.
"""
import contextlib
import threading
import time
from functools import lru_cache
from typing import Any

import numpy as np

from tarjim.tool_catalog import VOICEPRINT_REPO

FILE = "voxceleb_resnet34_LM.onnx"
CARD, PROCESSOR = "CUDAExecutionProvider", "CPUExecutionProvider"
NO_CARD: list[bool] = []  # set once the card refused the voice print in this run
RATE = 16000
LONGEST = 10.0  # seconds of a line that are enough to know the voice
AGAIN_SECONDS = 3600.0
TRIED: list[float] = []
LOCK = threading.Lock()


def fetched() -> bool:
    """Whether the model is here, fetching it when it is not (once an hour at most)."""
    from tarjim import model_pins

    if model_pins.ready(VOICEPRINT_REPO):
        return True
    with LOCK:
        if TRIED and time.time() - TRIED[-1] < AGAIN_SECONDS:
            return False
        TRIED.append(time.time())
    from tarjim.tools import online

    try:
        with online():
            model_pins.download(VOICEPRINT_REPO)
    except Exception as error:  # no voice print is no reason to fail a job
        print(f"speakers: the voice print model could not be fetched: {str(error)[:200]}")
        return False
    return model_pins.ready(VOICEPRINT_REPO)


@lru_cache(maxsize=1)
def session() -> Any:
    import onnxruntime

    from tarjim.model_pins import folder

    path = str(folder(VOICEPRINT_REPO) / FILE)
    if on_card(onnxruntime):
        try:
            return onnxruntime.InferenceSession(path, providers=[CARD, PROCESSOR])
        except Exception as error:  # the card's libraries are missing or do not fit: not a failure
            print(f"speakers: the voice print runs on the processor ({str(error)[:160]})",
                  flush=True)
    return onnxruntime.InferenceSession(path, providers=[PROCESSOR])


def on_card(onnxruntime: Any) -> bool:
    """Whether to try the card: tarjim uses it now (tarjim/device.py) and onnxruntime can."""
    from tarjim.device import best_device

    if NO_CARD or best_device() != "cuda" or CARD not in onnxruntime.get_available_providers():
        return False
    import torch  # noqa: F401  its CUDA libraries are the ones onnxruntime borrows

    preload = getattr(onnxruntime, "preload_dlls", None)
    if preload is not None:
        with contextlib.suppress(Exception):
            preload()
    return True


def embedded(feats: np.ndarray) -> np.ndarray:
    """The network's answer; a card that fails here hands every later line to the processor."""
    try:
        return np.asarray(session().run(["embs"], {"feats": feats[None]})[0][0], dtype=np.float64)
    except Exception as error:
        if NO_CARD or session().get_providers()[0] == PROCESSOR:
            raise
        print(f"speakers: the card did not take the voice print ({str(error)[:160]}); the "
              "processor does it from here", flush=True)
        NO_CARD.append(True)
        session.cache_clear()
        return np.asarray(session().run(["embs"], {"feats": feats[None]})[0][0], dtype=np.float64)


def features(clip: np.ndarray) -> np.ndarray:
    """80 filter banks every 10 ms, as WeSpeaker was trained on, with the mean taken off."""
    import torch
    from torchaudio.compliance import kaldi

    wave = torch.from_numpy(np.asarray(clip, dtype=np.float32) * 32768.0)[None]
    banks = kaldi.fbank(wave, num_mel_bins=80, frame_length=25, frame_shift=10, dither=0.0,
                        sample_frequency=RATE, window_type="hamming", use_energy=False)
    result: np.ndarray = (banks - banks.mean(dim=0)).numpy()
    return result


def print_of(clip: np.ndarray) -> np.ndarray:
    """The voice print of a stretch of sound, its length one."""
    middle = max(0, (len(clip) - int(LONGEST * RATE)) // 2)
    feats = features(clip[middle:middle + int(LONGEST * RATE)])
    found = embedded(feats)
    norm: np.ndarray = found / (np.linalg.norm(found) or 1.0)
    return norm
