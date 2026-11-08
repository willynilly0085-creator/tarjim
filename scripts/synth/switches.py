"""The bench's switches on tarjim, each a patch for one cell (or, for the decode cache and the
processor, for the whole process).

    local    on: the real local listener (Qwen3-ASR) and its second opinion
             off: no local listener (second_opinion answers nothing, qwen_transcript raises)
             wrong: qwen_transcript answers the truth words, at their truth times, written in
                    Arabic-looking letters and called 'Arabic' (the 2026-11-08 Somali chant)
    voiceprint off: asr.voiceprint.fetched is False, so no voice check runs
    letters  weak: the aligner hears consonants only (an abjad stand-in)
             sparse: 60% of the aligner's letters dropped (kanji read as pinyin)
             wrong: 30% of them replaced by random letters
    cpu      CUDA_VISIBLE_DEVICES='' and torch.set_num_threads(2), before any model loads
    decode cache: the aligner's whole-clip MMS log-probs kept per clip in work/emissions and read
             back when the clip's samples (and the model, device and precision) are unchanged
"""
import contextlib
import hashlib
import json
import os
import random
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

import numpy as np

VOWELS = set("aeiouy")
SPARSE_DROP, WRONG_SHARE = 0.6, 0.3
ARABIC = dict(zip("abcdefghijklmnopqrstuvwxyz",
                  "ابكدفغهحيجكلمنوبقرستوفوكيز", strict=True))
ROTATE = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"

Truth = dict[str, Any]


def arabic_looking(text: str) -> str:
    """Latin letters as Arabic ones; Arabic letters moved three along, so they are wrong too."""
    out = []
    for ch in text.lower():
        if ch in ARABIC:
            out.append(ARABIC[ch])
        elif ch in ROTATE:
            out.append(ROTATE[(ROTATE.index(ch) + 3) % len(ROTATE)])
        else:
            out.append(ch)
    return "".join(out)


def wrong_transcript(truth: Truth) -> Any:
    from tarjim.asr.base import Transcript
    from tarjim.models import Word

    words = [Word(arabic_looking(w["text"]), float(w["start"]), float(w["end"]))
             for w in sorted(truth["words"], key=lambda w: w["start"])]
    return Transcript(language="Arabic", text=" ".join(w.text for w in words), words=words)


def blocked(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError("bench: the real cloud is never called")


def local_patches(mode: str, truth: Truth) -> list[Any]:
    if mode == "on":
        return []
    if mode == "off":
        return [mock.patch("tarjim.hearing.second_opinion", lambda *_a, **_k: []),
                mock.patch("tarjim.hearing.qwen_transcript", blocked)]
    if mode == "wrong":
        made = wrong_transcript(truth)
        return [mock.patch("tarjim.hearing.qwen_transcript", lambda *_a, **_k: made)]
    raise ValueError(f"local mode {mode!r}")


def letters_patch(mode: str, seed: int) -> list[Any]:
    if mode in ("", "none"):
        return []
    from tarjim.asr.align import AlignEngine

    real = AlignEngine.tokens

    def tokens(self: Any, text: str) -> list[int]:
        found: list[int] = real(self, text)
        letters = {v: k for k, v in self.emitter.vocab.items()}
        rng = random.Random(f"{seed}:{mode}:{text}")
        if mode == "weak":
            return [t for t in found if letters.get(t, "") not in VOWELS]
        if mode == "sparse":
            return [t for t in found if rng.random() >= SPARSE_DROP]
        if mode == "wrong":
            pool = [self.emitter.vocab[c] for c in ARABIC if c in self.emitter.vocab]
            return [rng.choice(pool) if rng.random() < WRONG_SHARE else t for t in found]
        raise ValueError(f"letters mode {mode!r}")

    return [mock.patch.object(AlignEngine, "tokens", tokens)]


def voiceprint_patch(on: bool) -> list[Any]:
    return [] if on else [mock.patch("tarjim.asr.voiceprint.fetched", lambda: False)]


@contextlib.contextmanager
def applied(patches: list[Any]) -> Iterator[None]:
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield


def cpu_first() -> None:
    """The processor only, two threads: call before torch is imported anywhere."""
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch

    torch.set_num_threads(2)


class DecodeCache:
    """Whole-clip MMS log-probs per clip, kept under `folder` by the clip's samples."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.hits = self.misses = 0
        self.clip = ""  # named in the index, for a person looking at the folder

    def install(self) -> None:
        """Before the aligner is made: Letters holds the method it finds then."""
        from tarjim.asr.ctc import Emitter

        real = Emitter.heard
        cache = self

        def heard(emitter: Any, wav: Any) -> np.ndarray:
            return cache.read(emitter, wav, real)

        Emitter.heard = heard  # type: ignore[method-assign]

    def key(self, emitter: Any, wav: Any) -> str:
        samples = np.ascontiguousarray(np.asarray(wav, dtype=np.float32))
        digest = hashlib.sha256(samples.tobytes())
        digest.update(f"{emitter.MODEL}|{emitter.device}|{emitter.dtype}|{emitter.WINDOW}|"
                      f"{emitter.OVERLAP}".encode())
        return digest.hexdigest()[:24]

    def read(self, emitter: Any, wav: Any, real: Any) -> np.ndarray:
        path = self.folder / f"{self.key(emitter, wav)}.npy"
        if path.exists():
            self.hits += 1
            return np.load(path)
        self.misses += 1
        found: np.ndarray = real(emitter, wav)
        self.folder.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part.npy")
        np.save(part, found)
        part.replace(path)
        self.indexed(path.stem, len(wav))
        return found

    def indexed(self, key: str, samples: int) -> None:
        index = self.folder / "index.json"
        try:
            known = json.loads(index.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            known = {}
        known[key] = {"clip": self.clip, "seconds": round(samples / 16000, 2)}
        index.write_text(json.dumps(known, indent=1), encoding="utf-8")
