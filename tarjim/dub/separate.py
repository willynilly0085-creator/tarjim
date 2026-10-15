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
    except (ImportError, RuntimeError, OSError) as error:
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
    import torch
    from demucs.apply import apply_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = separation_model().to(device).eval()
    if model.samplerate != RATE:
        raise RuntimeError("unexpected demucs sample rate")
    wav = torch.from_numpy(mixture.T.copy())
    reference = wav.mean(0)
    scale = reference.std() + 1e-8
    normal = (wav - reference.mean()) / scale
    with torch.inference_mode():
        stems = apply_model(model, normal[None].to(device), device=device, split=True,
                            overlap=0.25)[0]
    stems = stems * scale + reference.mean()
    vocals_at = model.sources.index("vocals")
    vocals = stems[vocals_at]
    background = stems.sum(0) - vocals
    return vocals.cpu().numpy().T, background.cpu().numpy().T
