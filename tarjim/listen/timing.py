"""Word times for lines: the forced aligner, then the local listener's times where the aligner put a
line's words outside it (asr/fuse.py). Lines added after the first alignment are aligned in their
own stretch of sound, whose letters are read from those the aligner heard in the whole clip once
(asr/letters.Piece), so the clip is never heard again in full or in part (2026-11-08). Lines far
apart are aligned each in its own stretch, since one search over both pulled the words of a line
at 130 s to 198 s and 232 s, toward the other line at 234 s (2026-11-08)."""
from dataclasses import dataclass, replace
from typing import Any

from tarjim import guards
from tarjim.asr.agree import share_scored
from tarjim.asr.fuse import fuse
from tarjim.asr.letters import piece
from tarjim.asr.speechmap import SpeechMap
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import joined, split_words

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
    # the clip's speech map (asr/speechmap.py): a stretch reads its part of it (2026-11-09)
    speech: SpeechMap | None = None

    def whole(self, utterances: list[Utterance]) -> list[Word]:
        return fuse(*kept_lines(*self.aligned(self.wav, utterances), utterances), self.opinion)

    def part(self, utterances: list[Utterance]) -> list[Word]:
        return [w for group in apart(utterances) for w in self.stretch(group)]

    def stretch(self, utterances: list[Utterance]) -> list[Word]:
        if not utterances:
            return []
        sound = piece(self.wav, self.rate, min(u.start for u in utterances) - MARGIN,
                      max(u.end for u in utterances) + MARGIN)
        low = sound.start
        moved = [replace(u, start=u.start - low, end=u.end - low) for u in utterances]
        found, dropped = self.aligned(sound, moved)
        words = [replace(w, start=w.start + low, end=w.end + low) for w in found]
        return fuse(*kept_lines(words, dropped, utterances), self.opinion)

    def agreement(self, words: list[Word]) -> float | None:
        """The share of words said where they are timed (asr/agree.py); None when it cannot
        be told. Read from the runs' scores (2026-11-09), given here once for this timing."""
        found = run_scored(self.wav, words) if words else None
        return share_scored(found) if found else None

    def passes(self) -> int:
        """How often the aligner heard this clip's letters (asr/letters.Letters); 0 when it cannot
        be told. The aligner is already made: the check above made it."""
        from tarjim.asr.align import shared_aligner
        from tarjim.asr.letters import Letters

        letters = getattr(getattr(shared_aligner(), "emitter", None), "emissions", None)
        return letters.count(self.wav) if isinstance(letters, Letters) else 0

    def aligned(self, sound: Any, utterances: list[Utterance]) -> tuple[list[Word], set[int]]:
        """The words, and those of them the tolerant aligner dropped as written twice."""
        from tarjim.asr.align import shared_aligner
        from tarjim.memory import heavy

        engine = shared_aligner()
        with heavy():
            words = engine.align(sound, utterances, self.language, self.speech)
        return words, set(getattr(engine, "dropped", ()))


def run_scored(wav: Any, words: list[Word]) -> list[Word] | None:
    """The words with their run's strict score (asr/agree.scored), from the clip's letters heard
    once; None for a stand-in aligner with no ears. Read on the final words, after the voices
    gave each its speaker (listen/heard_align.py), so a run's score is the one it is shown with
    (2026-11-09)."""
    from tarjim.asr.agree import scored, scorer
    from tarjim.asr.align import shared_aligner
    from tarjim.memory import heavy

    with heavy():
        score = scorer(shared_aligner(), wav)
        return scored(words, score) if score else None


def final_scores(wav: Any, words: list[Word]) -> list[Word]:
    """The words as shown with their run's strict score, when the aligner is in memory: the
    timing made it, or a test put a stand-in there; it is never loaded for this alone."""
    from tarjim.asr import align

    info = getattr(align.shared_aligner, "cache_info", None)
    made = info is None or info().currsize > 0
    return (run_scored(wav, words) if made and words else None) or words


def kept_lines(words: list[Word], dropped: set[int],
               utterances: list[Utterance]) -> tuple[list[Word], list[Utterance]]:
    """The words less those dropped as written twice (asr/unplaced.py), and the lines with what
    is left of them: a line whose words all went goes too (2026-11-09)."""
    if not dropped:
        return words, utterances
    kept: list[Word] = []
    lines: list[Utterance] = []
    cursor = 0
    for line in utterances:
        size = len(split_words(line.text))
        mine = [w for k, w in enumerate(words[cursor:cursor + size], cursor) if k not in dropped]
        cursor += size
        text = joined([w.text for w in mine])
        if len(mine) < size and len(split_words(text)) != len(mine):
            mine, text = words[cursor - size:cursor], line.text  # its words cannot be told apart
        if mine:
            kept += mine
            lines.append(replace(line, text=text) if len(mine) < size else line)
    return kept, lines
