"""Word times for lines: the forced aligner, then the local listener's times where the aligner put a
line's words outside it (asr/fuse.py). Lines added after the first alignment are aligned in their
own stretch of sound, whose letters are read from those the aligner heard in the whole clip once
(asr/letters.Piece), so the clip is never heard again in full or in part (2026-11-08). Lines far
apart are aligned each in its own stretch, since one search over both pulled the words of a line
at 130 s to 198 s and 232 s, toward the other line at 234 s (2026-11-08)."""
from dataclasses import dataclass, replace
from typing import Any

from tarjim import guards
from tarjim.asr.fuse import fuse
from tarjim.asr.letters import piece
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

MARGIN = 5.0  # seconds of sound either side of the lines aligned on their own


def apart(utterances: list[Utterance]) -> list[list[Utterance]]:
    """The lines in groups whose stretches of sound would meet, in their order."""
    groups: list[list[Utterance]] = []
    for line in utterances:
        if groups and line.start - max(u.end for u in groups[-1]) <= 2 * MARGIN:
            groups[-1].append(line)
        else:
            groups.append([line])
    guards.when("timing.apart", len(groups) > 1)
    return groups


@dataclass(frozen=True)
class Timer:
    wav: Any
    rate: int
    language: str
    opinion: list[Word]  # the words this computer heard, possibly none

    def whole(self, utterances: list[Utterance]) -> list[Word]:
        return fuse(self.aligned(self.wav, utterances), utterances, self.opinion)

    def part(self, utterances: list[Utterance]) -> list[Word]:
        return [w for group in apart(utterances) for w in self.stretch(group)]

    def stretch(self, utterances: list[Utterance]) -> list[Word]:
        if not utterances:
            return []
        sound = piece(self.wav, self.rate, min(u.start for u in utterances) - MARGIN,
                      max(u.end for u in utterances) + MARGIN)
        low = sound.start
        moved = [replace(u, start=u.start - low, end=u.end - low) for u in utterances]
        words = [replace(w, start=w.start + low, end=w.end + low)
                 for w in self.aligned(sound, moved)]
        return fuse(words, utterances, self.opinion)

    def agreement(self, words: list[Word]) -> float | None:
        """The share of words said where they are timed (asr/agree.py); None when it cannot
        be told."""
        from tarjim.asr.agree import scorer, share_found
        from tarjim.asr.align import shared_aligner
        from tarjim.memory import heavy

        with heavy():
            score = scorer(shared_aligner(), self.wav)
            return share_found(score, words) if score and words else None

    def passes(self) -> int:
        """How often the aligner heard this clip's letters (asr/letters.Letters); 0 when it cannot
        be told. The aligner is already made: the check above made it."""
        from tarjim.asr.align import shared_aligner
        from tarjim.asr.letters import Letters

        letters = getattr(getattr(shared_aligner(), "emitter", None), "emissions", None)
        return letters.count(self.wav) if isinstance(letters, Letters) else 0

    def aligned(self, sound: Any, utterances: list[Utterance]) -> list[Word]:
        from tarjim.asr.align import shared_aligner
        from tarjim.memory import heavy

        with heavy():
            return shared_aligner().align(sound, utterances, self.language)
