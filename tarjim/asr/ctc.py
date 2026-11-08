import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

FRAME = 0.02
BLANK = 0
NEG = -1e30
OUTSIDE_PENALTY = 3.0
EPSILON = 1e-6  # of a frame: 19.5 s is frame 975, not 974.99

Span = tuple[float, float, float]
Bounds = tuple[np.ndarray, np.ndarray]


def labels_for(tokens: list[int]) -> np.ndarray:
    labels = np.full(2 * len(tokens) + 1, BLANK, dtype=np.int64)
    labels[1::2] = tokens
    return labels


def skip_mask(labels: np.ndarray) -> np.ndarray:
    mask = np.zeros(len(labels), dtype=bool)
    mask[3::2] = labels[3::2] != labels[1:-2:2]
    return mask


def step(scores: np.ndarray, skip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    one = np.concatenate(([NEG], scores[:-1]))
    two = np.where(skip, np.concatenate(([NEG, NEG], scores[:-2])), NEG)
    candidates = np.stack([scores, one, two])
    return candidates.max(axis=0), candidates.argmax(axis=0).astype(np.int8)


def state_bounds(frames: int, bounds: Bounds | None, states: int) -> Bounds:
    low, high = np.zeros(states, dtype=np.int64), np.full(states, frames, dtype=np.int64)
    if bounds is not None:
        low[1::2], high[1::2] = bounds
    return low, high


def emission(logp: np.ndarray, labels: np.ndarray, window: Bounds, t: int) -> np.ndarray:
    low, high = window
    result: np.ndarray = logp[t, labels] - OUTSIDE_PENALTY * ((t < low) | (t >= high))
    return result


def viterbi(logp: np.ndarray, labels: np.ndarray, bounds: Bounds | None = None) -> np.ndarray:
    skip = skip_mask(labels)
    window = state_bounds(len(logp), bounds, len(labels))
    scores = np.full(len(labels), NEG)
    scores[:2] = emission(logp, labels, window, 0)[:2]
    back = np.zeros((len(logp), len(labels)), dtype=np.int8)
    for t in range(1, len(logp)):
        scores, back[t] = step(scores, skip)
        scores = scores + emission(logp, labels, window, t)
    state = len(labels) - 1 if scores[-1] >= scores[-2] else len(labels) - 2
    path = np.empty(len(logp), dtype=np.int64)
    for t in range(len(logp) - 1, -1, -1):
        path[t] = state
        state -= int(back[t, state])
    return path


def token_spans(
        logp: np.ndarray, tokens: list[int], bounds: Bounds | None = None) -> list[Span] | None:
    if not tokens or len(logp) < len(tokens):
        return None
    labels = labels_for(tokens)
    path = viterbi(logp, labels, bounds)
    frames: list[list[int]] = [[] for _ in tokens]
    for t, state in enumerate(path):
        if state % 2:
            frames[(state - 1) // 2].append(t)
    if any(not f for f in frames):
        return None
    return [span_of(logp, f, tokens[k]) for k, f in enumerate(frames)]


def span_of(logp: np.ndarray, frames: list[int], token: int) -> Span:
    score = float(np.exp(logp[frames, token]).mean())
    return frames[0] * FRAME, (frames[-1] + 1) * FRAME, score


Key = tuple[int, int, bytes]


def fingerprint(wav: Any) -> Key:
    """The same sound: the same array, length and samples taken across it."""
    samples = np.asarray(wav, dtype=np.float32)
    return id(wav), len(samples), samples[:: max(1, len(samples) // 64)].tobytes()


@dataclass(frozen=True)
class Piece:
    """A stretch of a longer sound that knows where it sits in it, so its letters are read from
    the whole sound's, heard once, and the stretch is never heard again (2026-11-08)."""
    clip: Any
    rate: int
    first: int  # the whole sound's frame it starts on
    past: int  # the frame it ends before

    @property
    def start(self) -> float:
        return self.first * FRAME

    def sound(self) -> Any:
        hop = self.rate * FRAME
        return self.clip[round(self.first * hop):round(self.past * hop)]

    def __len__(self) -> int:
        return len(self.sound())

    def __getitem__(self, key: Any) -> Any:
        return self.sound()[key]

    def __array__(self, dtype: Any = None, copy: bool | None = None) -> np.ndarray:
        return np.asarray(self.sound(), dtype=dtype)


def piece(clip: Any, rate: int, low: float, high: float) -> Piece:
    """The sound from low to high seconds, widened to whole frames of the clip."""
    return Piece(clip, rate, int(max(0.0, low) / FRAME + EPSILON),
                 math.ceil(high / FRAME - EPSILON))


class Letters:
    """The letters heard in one whole sound, kept for that sound alone, so a weak computer holds
    one clip's (about 45 MB for two hours) and a slice or a check never hears it again."""

    def __init__(self, hear: Callable[[Any], np.ndarray]) -> None:
        self.hear = hear
        self.last: tuple[Key, np.ndarray] | None = None
        self.passes: tuple[Key | None, int] = (None, 0)

    def __call__(self, wav: Any) -> np.ndarray:
        if isinstance(wav, Piece):
            return self(wav.clip)[wav.first:wav.past]
        key = fingerprint(wav)
        if self.last is None or self.last[0] != key:
            self.last = None  # the clip before is let go before the next is heard
            self.last = (key, self.hear(wav))
            self.passes = (key, self.passes[1] + 1 if self.passes[0] == key else 1)
        return self.last[1]

    def tell(self, wav: Any) -> None:
        """How often the whole clip was heard, said once its lines are timed: once is right."""
        count = self.passes[1] if self.passes[0] == fingerprint(wav) else 0
        print(f"timing: the aligner heard the clip's letters {count} time(s)", flush=True)


class Emitter:
    MODEL = "MahmoudAshraf/mms-300m-1130-forced-aligner"
    WINDOW = 30.0
    OVERLAP = 1.0
    RATE = 16000

    def __init__(self, device: str | None = None) -> None:
        import torch
        from transformers import AutoModelForCTC, AutoTokenizer

        from tarjim.device import best_device, precision
        from tarjim.model_pins import folder

        self.torch = torch
        self.device = device or best_device()
        self.dtype = precision(self.device, torch.float16)
        where = folder(self.MODEL)
        self.model = AutoModelForCTC.from_pretrained(where, dtype=self.dtype,
                                                     use_safetensors=True)
        self.model = self.model.to(self.device).eval()
        tokenizer = AutoTokenizer.from_pretrained(where)
        self.vocab: dict[str, int] = tokenizer.get_vocab()
        # a stretch (Piece) and the check after timing (asr/agree.py) read the clip's from here
        self.emissions = Letters(self.heard)

    def heard(self, wav: Any) -> np.ndarray:
        total, hop = len(wav) / self.RATE, self.WINDOW - 2 * self.OVERLAP
        parts, start = [], 0.0
        while start < total:
            low, high = max(0.0, start - self.OVERLAP), min(total, start + hop + self.OVERLAP)
            logp = self.run(wav[int(low * self.RATE):int(high * self.RATE)])
            skip = round((start - low) / FRAME)
            keep = round((min(total, start + hop) - start) / FRAME)
            parts.append(logp[skip:skip + keep])
            start += hop
        return np.concatenate(parts)

    def run(self, clip: Any) -> np.ndarray:
        torch = self.torch
        audio = torch.from_numpy(np.asarray(clip, dtype=np.float32))
        audio = (audio - audio.mean()) / (audio.std() + 1e-7)
        with torch.inference_mode():
            logits = self.model(audio[None].to(self.device, self.dtype)).logits[0]
        result: np.ndarray = torch.log_softmax(logits.float(), dim=-1).cpu().numpy()
        return result
