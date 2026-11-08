"""Whose voice a stretch of sound is: a voice print, 256 numbers that are close for one voice.

WeSpeaker's ResNet34 (trained on VoxCeleb, CC-BY-4.0) is one 26 MB ONNX file run by onnxruntime on
the processor, a few hundredths of a second a line, so it runs on any computer. It comes with the
timing tool; a computer that set tarjim up before it existed fetches it the first time it is
needed, and until then, or when it cannot be fetched, the listener's labels stand as they are.
"""
import threading
import time
from functools import lru_cache
from typing import Any

import numpy as np

from tarjim.tool_catalog import VOICEPRINT_REPO

FILE = "voxceleb_resnet34_LM.onnx"
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

    path = folder(VOICEPRINT_REPO) / FILE
    return onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])


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
    found = np.asarray(session().run(["embs"], {"feats": feats[None]})[0][0], dtype=np.float64)
    norm: np.ndarray = found / (np.linalg.norm(found) or 1.0)
    return norm
