"""What the decode bench (decode_bench.py) hears with: each clip's whole-clip letters (the timing
bench's decode cache, else heard once and kept), its speech regions (kept too), and a word's
letters as asr/align.AlignEngine.tokens reads them, optionally spoilt like the timing bench's
--letters switch (sparse: 60% dropped; wrong: 30% replaced by random letters), 2026-11-08."""
import json
import random
from pathlib import Path
from typing import Any

import decode_text
import numpy as np

SPECIAL_IDS = 4  # as asr/align.SPECIAL_IDS
SPARSE_DROP, WRONG_SHARE = 0.6, 0.3
SAME_SECONDS = 0.5  # a cached clip this close in length is the same clip


def pool(folders: list[Path], folder: Path) -> list[decode_text.Line]:
    """Lines of the other clips in the same language: what an invented line says."""
    def truth(p: Path) -> dict[str, Any]:
        found: dict[str, Any] = json.loads((p / "truth.json").read_text(encoding="utf-8"))
        return found

    language = truth(folder)["language"]
    return [line for p in folders if p != folder and truth(p)["language"] == language
            for line in decode_text.lines_of(truth(p))]


class Ears:
    def __init__(self, synth: Path, letters: str, seed: int) -> None:
        from transformers import AutoTokenizer
        from uroman import Uroman

        from tarjim.asr.ctc import Emitter
        from tarjim.model_pins import folder

        self.synth, self.letters, self.seed = synth, letters, seed
        self.vocab: dict[str, int] = AutoTokenizer.from_pretrained(
            folder(Emitter.MODEL)).get_vocab()
        self.roman = Uroman()
        self.kept = synth / "work" / "decode_bench"
        self.emitter: Any = None
        self.language = "English"

    def said(self, words: list[str]) -> list[str]:
        from tarjim.asr.numbers import said

        return said(words, self.language)

    def tokens(self, text: str) -> list[int]:
        roman = self.roman.romanize_string(text).lower()
        found = [self.vocab[ch] for ch in roman if self.vocab.get(ch, 0) >= SPECIAL_IDS]
        rng = random.Random(f"{self.seed}:{self.letters}:{text}")
        if self.letters == "sparse":
            return [t for t in found if rng.random() >= SPARSE_DROP]
        if self.letters == "wrong":
            letters = [self.vocab[c] for c in "abcdefghijklmnopqrstuvwxyz" if c in self.vocab]
            return [rng.choice(letters) if rng.random() < WRONG_SHARE else t for t in found]
        return found

    def cached(self, clip: str, seconds: float) -> Path | None:
        """The timing bench's letters for the clip, by the name in its cache's index."""
        folder = self.synth / "work" / "emissions"
        try:
            index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        for key, entry in index.items():
            if entry.get("clip") == clip and abs(entry.get("seconds", 0) - seconds) < SAME_SECONDS:
                return folder / f"{key}.npy"
        return None

    def emissions(self, clip: Path, truth: dict[str, Any]) -> np.ndarray:
        found = self.cached(clip.name, truth["duration"])
        if found is not None and found.exists():
            return np.load(found)
        path = self.kept / f"{clip.name}.npy"
        if not path.exists():
            self.kept.mkdir(parents=True, exist_ok=True)
            np.save(path, self.heard(clip))
        return np.load(path)

    def heard(self, clip: Path) -> np.ndarray:
        import soundfile

        from tarjim.asr.ctc import Emitter

        if self.emitter is None:
            self.emitter = Emitter()
        wav, _ = soundfile.read(str(clip / "clip.wav"), dtype="float32")
        print(f"hearing {clip.name} on {self.emitter.device}", flush=True)
        return np.asarray(Emitter.heard(self.emitter, wav))

    def regions(self, clip: Path) -> list[tuple[float, float]]:
        path = self.kept / f"{clip.name}.speech.json"
        if path.exists():
            return [tuple(r) for r in json.loads(path.read_text(encoding="utf-8"))]
        import soundfile

        from tarjim.asr.vad import speech_regions

        wav, _ = soundfile.read(str(clip / "clip.wav"), dtype="float32")
        found = speech_regions(wav)
        self.kept.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(found), encoding="utf-8")
        return found
