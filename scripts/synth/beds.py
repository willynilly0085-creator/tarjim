"""Background beds: a synthetic music loop and pink noise, seeded and repeatable."""
from __future__ import annotations

import numpy as np
from audio import SR

CHORDS = ((220.0, 277.18, 329.63), (196.0, 246.94, 293.66),
          (174.61, 220.0, 261.63), (196.0, 246.94, 329.63))
BAR_S = 2.0


def _pad(n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, chord in enumerate(CHORDS * (int(n / SR / BAR_S) // len(CHORDS) + 1)):
        a, b = int(k * BAR_S * SR), min(n, int((k + 1) * BAR_S * SR))
        if a >= n:
            break
        seg = t[a:b] - t[a]
        env = np.minimum(1.0, seg / 0.08) * np.exp(-seg * 0.6)
        for f in chord + (chord[0] / 2,):
            phase = rng.uniform(0, 2 * np.pi)
            out[a:b] += env * (np.sin(2 * np.pi * f * seg + phase)
                               + 0.3 * np.sin(4 * np.pi * f * seg + phase))
    return out


def _drums(n: int, rng: np.random.Generator) -> np.ndarray:
    out = np.zeros(n)
    kick_t = np.arange(int(0.25 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 60 * np.exp(-kick_t * 30)) * kick_t) * np.exp(-kick_t * 14)
    hat = np.diff(rng.standard_normal(int(0.05 * SR) + 1)) * np.exp(-np.arange(int(0.05 * SR)) / 160)
    for beat in range(int(n / SR / 0.25)):
        a = int(beat * 0.25 * SR)
        src = kick * 1.5 if beat % 4 == 0 else hat * 0.25
        m = min(len(src), n - a)
        out[a:a + m] += src[:m]
    return out


def music(n: int, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return _pad(n, rng) + _drums(n, rng)


def noise(n: int, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    spec /= np.sqrt(np.maximum(f, 20.0))
    return np.fft.irfft(spec, n)


def bed(kind: str, n: int) -> np.ndarray:
    if kind == "music":
        return music(n)
    if kind == "noise":
        return noise(n)
    raise ValueError(kind)
