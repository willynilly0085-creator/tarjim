import subprocess
import wave
from pathlib import Path

import numpy as np

from tarjim.media import tool

RATE = 44100
MAX_SPEEDUP = 1.8
GENTLE = 1.02
QUIET = 0.01
EDGE_PAD = 0.04
FADE = 0.06
FFMPEG_SECONDS = 3600


def ffmpeg(args: list[str], data: bytes | None = None) -> bytes:
    try:
        result = subprocess.run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", *args],
                                input=data, capture_output=True, check=False,
                                timeout=FFMPEG_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg did not finish within an hour") from None
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-300:])
    return result.stdout


def decode(source: Path | bytes, channels: int = 1, rate: int = RATE) -> np.ndarray:
    feed = source if isinstance(source, bytes) else None
    target = "-" if feed is not None else str(source)
    raw = ffmpeg(["-i", target, "-vn", "-ac", str(channels), "-ar", str(rate), "-f", "f32le", "-"],
                 feed)
    samples = np.frombuffer(raw, dtype=np.float32).copy()
    return samples.reshape(-1, channels) if channels > 1 else samples


def resample(wav: np.ndarray, source: int, rate: int = RATE) -> np.ndarray:
    if source == rate or wav.size == 0:
        return wav.astype(np.float32)
    positions = np.arange(int(len(wav) * rate / source)) * (source / rate)
    stretched: np.ndarray = np.interp(positions, np.arange(len(wav)), wav).astype(np.float32)
    return stretched


def speed_up(wav: np.ndarray, factor: float, rate: int = RATE) -> np.ndarray:
    if factor <= GENTLE:
        return wav
    tempo = min(factor, MAX_SPEEDUP)
    raw = ffmpeg(["-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-",
                  "-filter:a", f"atempo={tempo:.3f}", "-f", "f32le", "-"], wav.tobytes())
    return np.frombuffer(raw, dtype=np.float32).copy() if raw else wav


def write_wav(path: Path, samples: np.ndarray, rate: int = RATE) -> Path:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    channels = 1 if pcm.ndim == 1 else pcm.shape[1]
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return path


def cut(samples: np.ndarray, spans: list[tuple[float, float]], rate: int = RATE) -> np.ndarray:
    pieces = [samples[int(a * rate):int(b * rate)] for a, b in spans]
    return np.concatenate(pieces) if pieces else samples[:0]


def trim(wav: np.ndarray, rate: int = RATE) -> np.ndarray:
    loud = np.flatnonzero(np.abs(wav) > QUIET)
    if loud.size == 0:
        return wav[:0]
    pad = int(EDGE_PAD * rate)
    return wav[max(0, loud[0] - pad):loud[-1] + pad]


def fit(wav: np.ndarray, seconds: float, rate: int = RATE) -> np.ndarray:
    limit = int(seconds * rate)
    if wav.size <= limit:
        return wav
    fade = min(int(FADE * rate), limit)
    clipped = wav[:limit].copy()
    clipped[limit - fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return clipped
