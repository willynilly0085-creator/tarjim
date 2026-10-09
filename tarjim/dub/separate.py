from dataclasses import dataclass
from pathlib import Path

import numpy as np

from tarjim.dub.audio import RATE, decode

BACKGROUND_WITHOUT_STEMS = 0.12


@dataclass
class Stems:
    voices: np.ndarray
    background: np.ndarray
    separated: bool


def separate(video: Path) -> Stems:
    mixture = decode(video, channels=2)
    try:
        voices, background = split_voices(mixture)
    except (ImportError, RuntimeError, OSError) as error:
        print(f"dubbing: voices not separated from the background ({type(error).__name__}); "
              "the original sound is kept quietly under the new voices", flush=True)
        mono = mixture.mean(axis=1)
        return Stems(mono, mixture * BACKGROUND_WITHOUT_STEMS, separated=False)
    return Stems(voices.mean(axis=1), background, separated=True)


def split_voices(mixture: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = get_model("htdemucs").to(device).eval()
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
