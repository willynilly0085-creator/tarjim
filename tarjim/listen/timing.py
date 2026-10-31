"""Word times for lines: the forced aligner, then the local listener's times where the aligner put a
line's words outside it (asr/fuse.py). Lines added after the first alignment are aligned in their
own stretch of sound, so a long clip is not run through the aligner again in full."""
from dataclasses import dataclass, replace
from typing import Any

from tarjim.asr.fuse import fuse
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

MARGIN = 5.0  # seconds of sound either side of the lines aligned on their own


@dataclass(frozen=True)
class Timer:
    wav: Any
    rate: int
    language: str
    opinion: list[Word]  # the words this computer heard, possibly none

    def whole(self, utterances: list[Utterance]) -> list[Word]:
        return fuse(self.aligned(self.wav, utterances), utterances, self.opinion)

    def part(self, utterances: list[Utterance]) -> list[Word]:
        if not utterances:
            return []
        low = max(0.0, min(u.start for u in utterances) - MARGIN)
        high = max(u.end for u in utterances) + MARGIN
        sound = self.wav[int(low * self.rate):int(high * self.rate)]
        moved = [replace(u, start=u.start - low, end=u.end - low) for u in utterances]
        words = [replace(w, start=w.start + low, end=w.end + low)
                 for w in self.aligned(sound, moved)]
        return fuse(words, utterances, self.opinion)

    def aligned(self, sound: Any, utterances: list[Utterance]) -> list[Word]:
        from tarjim.asr.align import shared_aligner
        from tarjim.memory import heavy

        with heavy():
            return shared_aligner().align(sound, utterances, self.language)
