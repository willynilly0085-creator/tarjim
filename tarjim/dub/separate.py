import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.dub.audio import RATE, decode

BACKGROUND_WITHOUT_STEMS = 0.12
REPO = "adefossez/HTDemucs"
KLASS = "demucs.htdemucs.HTDemucs"
PART = re.compile(r"[0-9a-f]{8}")
# Seconds separated at once: the whole of a long video at once filled the graphics card (5 GB
# for an hour) or, on the processor, about 15 GB of memory.
WINDOW = 180.0
CONTEXT = 5.0


@dataclass
class Stems:
    voices: np.ndarray
    background: np.ndarray
    separated: bool


def separate(video: Path) -> Stems:
    from tarjim.memory import heavy

    mixture = decode(video, channels=2)
    try:
        with heavy():
            voices, background = split_voices(mixture)
    except (ImportError, RuntimeError, OSError, MemoryError) as error:
        print(f"dubbing: voices not separated from the background ({type(error).__name__}); "
              "the original sound is kept quietly under the new voices", flush=True)
        mono = mixture.mean(axis=1)
        return Stems(mono, mixture * BACKGROUND_WITHOUT_STEMS, separated=False)
    return Stems(voices.mean(axis=1), background, separated=True)


def pinned_folder() -> Path:
    """The voice separation model at its pinned commit, fetched on the first dub."""
    from tarjim import model_pins

    if not model_pins.ready(REPO):
        from tarjim.tools import online

        with online():
            model_pins.download(REPO)
    return model_pins.folder(REPO)


def checked_part(path: Path) -> Any:
    """demucs builds whatever class a weights file names; only HTDemucs itself is accepted."""
    from safetensors import safe_open

    with safe_open(str(path), framework="pt") as file:
        metadata = file.metadata() or {}
    if metadata.get("klass") != KLASS or "structure" in metadata:
        raise RuntimeError("the voice separation model is not the one tarjim checked")
    from demucs.hf import load_safetensors_model

    return load_safetensors_model(path)


def separation_model() -> Any:
    """Never demucs' own get_model: it falls back to a pickled download when the hub is off."""
    import yaml

    where = pinned_folder()
    bag = yaml.safe_load((where / "htdemucs.yaml").read_text(encoding="utf-8"))
    parts = [str(sig) for sig in bag.get("models", [])]
    if not parts or not all(PART.fullmatch(sig) for sig in parts):
        raise RuntimeError("the voice separation model is not the one tarjim checked")
    models = [checked_part(where / f"{sig}.safetensors") for sig in parts]
    from demucs.apply import BagOfModels

    return BagOfModels(models, bag.get("weights"), bag.get("segment"))


def split_voices(mixture: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A window at a time, each heard with CONTEXT on both sides so the joins do not show. The
    level is the whole sound's, so every window is scaled alike."""
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = separation_model().to(device).eval()
    if model.samplerate != RATE:
        raise RuntimeError("unexpected demucs sample rate")
    centre = float(mixture.mean())
    scale = float(mixture.mean(axis=1).std()) + 1e-8
    vocals, background = np.empty_like(mixture), np.empty_like(mixture)
    step, context = int(WINDOW * RATE), int(CONTEXT * RATE)
    for start in range(0, len(mixture), step):
        heard = slice(max(0, start - context), min(len(mixture), start + step + context))
        stems = separated(model, (mixture[heard] - centre) / scale, device) * scale + centre
        kept = slice(start - heard.start, start - heard.start + min(step, len(mixture) - start))
        voice = stems[model.sources.index("vocals")][kept]
        vocals[start:start + len(voice)] = voice
        background[start:start + len(voice)] = stems.sum(0)[kept] - voice
    return vocals, background


def separated(model: Any, piece: np.ndarray, device: str) -> np.ndarray:
    """The stems of one window, as (stem, sample, channel). The sound stays in memory and only
    the model's own steps run on the device, so the card holds a few seconds at a time."""
    import torch
    from demucs.apply import apply_model

    wav = torch.from_numpy(np.ascontiguousarray(piece.T, dtype=np.float32))
    with torch.inference_mode():
        stems = apply_model(model, wav[None], device=device, split=True, overlap=0.25)[0]
    found: np.ndarray = stems.cpu().numpy().transpose(0, 2, 1)
    return found
