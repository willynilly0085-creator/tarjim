"""Words given times without the aligner's ears: a line spread over its own time by the length of
its words, and the words the aligner could not place sharing the time between their neighbours.
Moved out of asr/align.py on 2026-11-08, unchanged, to make room there; align.py still offers
them by their old names."""
from dataclasses import dataclass

from tarjim.asr.qwen import core
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import split_words

GAP_FALLBACK = 0.2
WORD_BASE = 0.3
WORD_PER_LETTER = 0.1


@dataclass
class Slot:
    text: str
    speaker: str
    owner: int
    start: float = 0.0
    end: float = 0.0
    timed: bool = False
    said: str = ""  # what the aligner listens for: a number spelled out, "" for none
    score: float | None = None  # the mean score of its letters, when the aligner heard them


def proportional(utterance: Utterance) -> list[Word]:
    tokens = split_words(utterance.text)
    weights = [max(1, len(core(token))) for token in tokens]
    step = (utterance.end - utterance.start) / max(1, sum(weights))
    words, cursor = [], utterance.start
    for token, weight in zip(tokens, weights, strict=True):
        words.append(Word(token, cursor, cursor + weight * step, utterance.speaker,
                          source="estimated"))
        cursor += weight * step
    return words


def longest(text: str) -> float:
    return WORD_BASE + WORD_PER_LETTER * len(core(text))


def runs(slots: list[Slot]) -> list[tuple[int, int]]:
    """Where each stretch of words the aligner could not place begins and ends."""
    found: list[tuple[int, int]] = []
    for index, slot in enumerate(slots):
        if slot.timed:
            continue
        if found and found[-1][1] == index:
            found[-1] = (found[-1][0], index + 1)
        else:
            found.append((index, index + 1))
    return found


def share(run: list[Slot], start: float, end: float) -> None:
    """The run's words take the time between their neighbours, each by its length."""
    weights = [longest(slot.text) for slot in run]
    step, cursor = (end - start) / sum(weights), start
    for slot, weight in zip(run, weights, strict=True):
        slot.start, cursor = cursor, cursor + weight * step
        slot.end = cursor
    run[-1].end = end


def fill_gaps(slots: list[Slot]) -> None:
    """Words the aligner could not place share the gap between the words around them, so a
    countdown "2, 1, 0" is not one word on screen for seconds and two crushed after it."""
    for first, past in runs(slots):
        count = past - first
        before = slots[first - 1].end if first else None
        after = slots[past].start if past < len(slots) else None
        if before is None:
            end = after if after is not None else GAP_FALLBACK * count
            start = max(0.0, end - GAP_FALLBACK * count)
        else:
            start = before
            end = max(start, after) if after is not None else start + GAP_FALLBACK * count
        share(slots[first:past], start, end)


def free(speech: list[tuple[float, float]], span: tuple[float, float],
         taken: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The speech inside the span less the stretches taken (asr/unplaced.py, 2026-11-09)."""
    found = [(max(a, span[0]), min(b, span[1])) for a, b in speech]
    for low, high in sorted(taken):
        found = [part for a, b in found
                 for part in ((a, min(b, low)), (max(a, high), b)) if part[1] > part[0]]
    return [(a, b) for a, b in found if b > a]
