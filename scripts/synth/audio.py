"""Audio helpers for the synthetic bench: WAV io, speech energy, word refinement, beds."""
from __future__ import annotations

import os
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 16000
HOP = SR // 100  # 10 ms frames
SPEECH_DB = -45.0  # TTS output is digitally clean; pauses sit far below this
PAUSE_FRAMES = 15  # a 150 ms silence inside a word slot means the next word began
FFMPEG = os.environ.get("TARJIM_FFMPEG", "ffmpeg")


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, np.int16).astype(np.float32) / 32768.0


def write_wav(path: Path, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def frame_db(x: np.ndarray) -> np.ndarray:
    n = len(x) // HOP
    frames = x[: n * HOP].reshape(n, HOP).astype(np.float64)
    return 20.0 * np.log10(np.sqrt(np.mean(frames**2, axis=1)) + 1e-9)


def rms_db(x: np.ndarray) -> float:
    return float(20.0 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9))


def shift_voice(src: Path, dst: Path, factor: float) -> None:
    """Move pitch and formants by `factor` while keeping the duration."""
    chain = f"asetrate={SR * factor:.3f},aresample={SR},atempo={1.0 / factor:.6f}"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-af", chain,
                    "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)], check=True)


def _last_pause(seg: np.ndarray) -> int | None:
    """Start frame of the last long silence in seg that has speech after it."""
    idx = np.flatnonzero(seg)
    if len(idx) < 2:
        return None
    long = np.flatnonzero(np.diff(idx) - 1 >= PAUSE_FRAMES)
    return int(idx[long[-1]] + 1) if len(long) else None


def refine(starts: list[float], x: np.ndarray) -> list[tuple[float, float]]:
    """Exact word (start, end) from engine word starts plus the energy envelope:
    each word is the speech inside its slot [start_i, start_i+1)."""
    speech = frame_db(x) > SPEECH_DB
    total = len(speech)
    lows = [int(round(s * 100)) for s in starts] + [total]
    out: list[tuple[float, float]] = []
    for i in range(len(starts)):
        lo, hi = lows[i], max(lows[i] + 1, lows[i + 1])
        pause = _last_pause(speech[lo:hi])
        if pause is not None and i + 1 < len(starts):
            hi = lo + pause  # engine boundary came late: the next word starts after the pause
            lows[i + 1] = min(lows[i + 1], lo + pause)
        idx = np.flatnonzero(speech[lo:hi])
        a, b = (lo + idx[0], lo + idx[-1] + 1) if len(idx) else (lo, hi)
        out.append((a / 100.0, max(b, a + 1) / 100.0))
    return out
