import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.dub.audio import decode
from tarjim.dub.lines import Line

BACKEND = "s2.1-pro"
PARALLEL = 4
TRIES = 2
PAUSE = 1.5


class FishVoices:
    def __init__(self, key: str, references: dict[str, Path], saved_voice: str = "") -> None:
        from fish_audio_sdk import Session

        self.session: Any = Session(key)
        self.owned: list[str] = []
        self.models = ({speaker: saved_voice for speaker in references} if saved_voice
                       else {speaker: self.upload(path) for speaker, path in references.items()})

    def upload(self, reference: Path) -> str:
        model = self.session.create_model(title="tarjim-temporary", voices=[reference.read_bytes()],
                                          texts=[""], visibility="private")
        self.owned.append(model.id)
        return str(model.id)

    def speak(self, line: Line) -> np.ndarray:
        from fish_audio_sdk import TTSRequest

        model = self.models.get(line.speaker) or next(iter(self.models.values()))
        request = TTSRequest(text=line.text, format="wav", reference_id=model, latency="normal")
        for _ in range(TRIES):
            try:
                return decode(b"".join(self.session.tts(request, backend=BACKEND)))
            except Exception:
                time.sleep(PAUSE)
        return np.zeros(0, dtype=np.float32)

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        try:
            with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
                return list(pool.map(self.speak, lines))
        finally:
            self.close()

    def close(self) -> None:
        for model in self.owned:
            try:
                self.session.delete_model(model)
            except Exception:
                continue
        self.owned.clear()
