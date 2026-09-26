from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np

from tarjim.asr.ctc import FRAME, Emitter, Span, token_spans
from tarjim.asr.qwen import core
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

CHUNK_SECONDS = 240.0
PAD = 2.0
EXTRA_TAG = "p"
MIN_EXTRA_SCORE = 0.3
SPECIAL_IDS = 4
GAP_FALLBACK = 0.2
WINDOW_MARGIN = 1.0
WORD_BASE = 0.3
WORD_PER_LETTER = 0.1


@dataclass
class Slot:
    text: str
    speaker: str
    owner: int
    start: float = 0.0
    end: float = 0.0
    score: float = 0.0
    timed: bool = False


def proportional(utterance: Utterance) -> list[Word]:
    tokens = utterance.text.split()
    weights = [max(1, len(core(token))) for token in tokens]
    step = (utterance.end - utterance.start) / max(1, sum(weights))
    words, cursor = [], utterance.start
    for token, weight in zip(tokens, weights, strict=True):
        words.append(Word(token, cursor, cursor + weight * step, utterance.speaker))
        cursor += weight * step
    return words


def chunks(utterances: list[Utterance]) -> list[list[Utterance]]:
    groups: list[list[Utterance]] = []
    for utterance in utterances:
        if groups and utterance.end - groups[-1][0].start <= CHUNK_SECONDS:
            groups[-1].append(utterance)
        else:
            groups.append([utterance])
    return groups


def windows(utterances: list[Utterance], low: int) -> tuple[np.ndarray, np.ndarray]:
    starts = np.array([(u.start - WINDOW_MARGIN) / FRAME - low for u in utterances])
    ends = np.array([(u.end + WINDOW_MARGIN) / FRAME - low for u in utterances])
    return starts.astype(np.int64), ends.astype(np.int64)


def densest(spans: list[Span], speech: np.ndarray) -> tuple[float, float]:
    groups = [[spans[0]]]
    for previous, current in pairwise(spans):
        between = speech[int(previous[1] / FRAME):int(current[0] / FRAME)]
        if not between.all():
            groups.append([])
        groups[-1].append(current)
    best = max(groups, key=len)
    return best[0][0], best[-1][1]


def longest(text: str) -> float:
    return WORD_BASE + WORD_PER_LETTER * len(core(text))


def fill_gaps(slots: list[Slot]) -> None:
    for index, slot in enumerate(slots):
        if slot.timed:
            continue
        slot.start = slots[index - 1].end if index else 0.0
        later = [s.start for s in slots[index + 1:] if s.timed]
        slot.end = later[0] if later else slot.start + GAP_FALLBACK
        slot.start = min(slot.start, slot.end)


def keep_real(slots: list[Slot]) -> list[Slot]:
    scores: dict[int, list[float]] = {}
    for slot in slots:
        if slot.timed:
            scores.setdefault(slot.owner, []).append(slot.score)
    doubtful = {owner for owner, values in scores.items() if np.mean(values) < MIN_EXTRA_SCORE}
    return [s for s in slots if not (s.speaker.startswith(EXTRA_TAG) and s.owner in doubtful)]


class AlignEngine:
    def __init__(self, device: str = "cuda:0") -> None:
        import uroman

        self.emitter = Emitter(device)
        self.roman = uroman.Uroman()

    def align(self, wav: Any, utterances: list[Utterance], language: str) -> list[Word]:
        from tarjim.asr.vad import mute_silence, speech_mask, speech_regions

        logp = self.emitter.emissions(wav)
        self.speech = speech_mask(speech_regions(wav), len(logp))
        logp = mute_silence(logp, self.speech)
        return [w for group in chunks(utterances) for w in self.align_group(logp, group)]

    def tokens(self, text: str) -> list[int]:
        vocab = self.emitter.vocab
        roman = self.roman.romanize_string(text).lower()
        return [vocab[ch] for ch in roman if vocab.get(ch, 0) >= SPECIAL_IDS]

    def align_group(self, logp: np.ndarray, group: list[Utterance]) -> list[Word]:
        low = max(0, int((group[0].start - PAD) / FRAME))
        high = min(len(logp), int((max(u.end for u in group) + PAD) / FRAME))
        slots = [Slot(tok, u.speaker, i) for i, u in enumerate(group) for tok in u.text.split()]
        if not self.time_slots(logp[low:high], slots, group, low):
            return [word for u in group for word in proportional(u)]
        fill_gaps(slots)
        return [Word(s.text, s.start, s.end, s.speaker) for s in keep_real(slots)]

    def time_slots(
            self, logp: np.ndarray, slots: list[Slot], group: list[Utterance], low: int) -> bool:
        owners = [(k, t) for k, s in enumerate(slots) for t in self.tokens(s.text)]
        bounds = windows([group[slots[k].owner] for k, _ in owners], low)
        spans = token_spans(logp, [t for _, t in owners], bounds)
        if spans is None:
            return False
        per_slot: dict[int, list[Span]] = {}
        for (k, _), (start, end, score) in zip(owners, spans, strict=True):
            per_slot.setdefault(k, []).append((start + low * FRAME, end + low * FRAME, score))
        for k, word in per_slot.items():
            slot = slots[k]
            start, slot.end = densest(word, self.speech)
            slot.start = max(start, slot.end - longest(slot.text))
            slot.score, slot.timed = max(s[2] for s in word), True
        return True
