from functools import lru_cache
from itertools import islice
from typing import Any, NamedTuple

import numpy as np

from tarjim import guards
from tarjim.asr.costs import Calibration, Calibrations, Costs
from tarjim.asr.ctc import FRAME, Emitter, Span, token_spans
from tarjim.asr.groups import WINDOW_MARGIN, chunks, densest, quietest, tell_evened, windows
from tarjim.asr.letters import Piece
from tarjim.asr.numbers import said
from tarjim.asr.speechmap import HARD, SOFT, SpeechMap
from tarjim.asr.spread import (
    GAP_FALLBACK,
    WORD_BASE,
    WORD_PER_LETTER,
    Slot,
    fill_gaps,
    longest,
    proportional,
    runs,
    share,
)
from tarjim.asr.tolerant import Text, tolerant_spans
from tarjim.asr.tolerated import heard_in, mended, priced
from tarjim.asr.unplaced import Region
from tarjim.asr.waited import TIGHT, waited
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word
from tarjim.scripts import split_words

OVERLAP = 1.0  # starting this far inside an earlier utterance: said over it, not after it
SHORT_REPLY = 4  # words: "Really?", "Oh my gosh", not a turn of its own
PAD = 2.0
SPECIAL_IDS = 4
# moved to asr/spread.py on 2026-11-08 and still offered here: fuse, piles, anchor and tests
# take them from this module
__all__ = ["GAP_FALLBACK", "WORD_BASE", "WORD_PER_LETTER", "Slot", "fill_gaps", "longest",
           "proportional", "runs", "share"]


class Reach(NamedTuple):
    """How far around its lines a group is searched: the sound cut out either side (pad), and
    the margin a letter is found in without a penalty (groups.windows)."""
    pad: float
    margin: float


WIDE = Reach(PAD, WINDOW_MARGIN)
OWN = Reach(TIGHT, TIGHT)  # a turn searched again inside its own time (asr/waited.py)


class Search(NamedTuple):
    group: list[Utterance]
    low: int  # the frame the searched sound starts at
    margin: float


def short(utterance: Utterance) -> bool:
    return len(split_words(utterance.text)) <= SHORT_REPLY


def overlapping(utterances: list[Utterance]) -> list[bool]:
    """Which short replies are said over an earlier turn ("Really?" inside the host's turn).
    Two long turns that overlap stay one after the other: each is read as a whole."""
    flags: list[bool] = []
    reach = float("-inf")
    for utterance in utterances:
        flags.append(utterance.start < reach - OVERLAP and short(utterance))
        if not flags[-1]:
            reach = max(reach, utterance.end)
    return flags


@lru_cache(maxsize=1)
def shared_aligner() -> "AlignEngine":
    return AlignEngine()


class AlignEngine:
    calibrations: Calibrations  # the clip's prices in the tolerant mode (asr/tolerated.py)
    calibration: Calibration | None = None
    costs: Costs | None = None  # None: the strict reading
    hard: np.ndarray  # the frames of silence for sure, where the star never sits
    dropped: set[int]  # the words the last alignment dropped as written twice
    unplaced: list[Region]  # ...and where it spread the words the sound did not hold

    def __init__(self, device: str | None = None) -> None:
        import uroman

        self.emitter = Emitter(device)
        self.roman = uroman.Uroman()

    def align(self, wav: Any, utterances: list[Utterance], language: str,
              speech: SpeechMap | None = None) -> list[Word]:
        self.language, self.dropped, self.unplaced = language, set(), []
        self.evened: list[Utterance] = []  # lines spread evenly, told once at the end
        heard, view = heard_in(wav, self.emitter.emissions(wav), speech, utterances)
        self.speech, self.hard, logp = view.tier >= SOFT, view.tier == HARD, heard.logp
        over = overlapping(utterances)
        guards.fired("align.said_over", sum(over))  # here, not in overlapping: fuse asks it too
        turns = [u for u, said_over in zip(utterances, over, strict=True) if not said_over]
        self.costs = None  # strict while the clip's prices are measured (2026-11-09)
        self.calibration = priced(self, wav, heard, turns)
        self.costs = self.calibration.costs if self.calibration else None
        timed = iter([w for group in chunks(turns) for w in self.align_group(logp, group)])
        # one search keeps words in order, so a reply said over a turn is searched on its own
        words = [w for u, said_over in zip(utterances, over, strict=True)
                 for w in (self.align_group(logp, [u]) if said_over
                           else islice(timed, len(split_words(u.text))))]
        self.unwaited(logp, utterances, over, words)
        if self.costs is not None:  # the tolerant mode, the clip's prices measured
            words = mended(self, heard, utterances, words)
        tell_evened(self.evened, wav.start if isinstance(wav, Piece) else 0.0)
        return words

    def tokens(self, text: str) -> list[int]:
        vocab = self.emitter.vocab
        roman = self.roman.romanize_string(text).lower()
        return [vocab[ch] for ch in roman if vocab.get(ch, 0) >= SPECIAL_IDS]

    def unwaited(self, logp: np.ndarray, utterances: list[Utterance], over: list[bool],
                 words: list[Word]) -> None:
        """A turn the one search made wait for the turn it was said over gets the times its own
        search inside its own time gives, when they start earlier (asr/waited.py)."""
        moved = 0
        for index, first in waited(utterances, over, words):
            evened = len(self.evened)
            alone = self.align_group(logp, [utterances[index]], OWN)
            if len(self.evened) == evened and alone[0].start < words[first].start:
                words[first:first + len(alone)] = alone
                moved += 1
            del self.evened[evened:]  # not followed alone: the first search's times stay
        guards.fired("align.unwaited", moved)

    def align_group(
            self, logp: np.ndarray, group: list[Utterance], reach: Reach = WIDE) -> list[Word]:
        """The group's words where their letters are heard. A group that cannot be followed
        whole is cut at its longest silence and each half tried on its own; only a line that
        still cannot be, or text with no letters at all, is spread evenly (2026-11-08)."""
        low = max(0, int((group[0].start - reach.pad) / FRAME))
        high = min(len(logp), int((max(u.end for u in group) + reach.pad) / FRAME))
        slots = [Slot(tok, u.speaker, i) for i, u in enumerate(group)
                 for tok in split_words(u.text)]
        for slot, sound in zip(slots, said([s.text for s in slots], self.language), strict=True):
            slot.said = sound
        if self.time_slots(logp[low:high], slots, Search(group, low, reach.margin)):
            fill_gaps(slots)
            return [Word(s.text, s.start, s.end, s.speaker, score=s.score,
                         source="aligned" if s.timed else "unplaced") for s in slots]
        if len(group) > 1 and any(self.tokens(s.said) for s in slots):
            cut = quietest(group, self.speech)
            halves = group[:cut], group[cut:]
            return [w for half in halves for w in self.align_group(logp, half, reach)]
        self.evened.extend(group)
        return [word for u in group for word in proportional(u)]

    def time_slots(self, logp: np.ndarray, slots: list[Slot], search: Search) -> bool:
        owners = [(k, t) for k, s in enumerate(slots) for t in self.tokens(s.said)]
        group, low = search.group, search.low
        bounds = windows([group[slots[k].owner] for k, _ in owners], low, search.margin)
        spans = self.read(logp, Text([t for _, t in owners], [k for k, _ in owners], bounds), low)
        if spans is None:
            return False
        per_slot: dict[int, list[Span]] = {}
        for (k, _), (start, end, score) in zip(owners, spans, strict=True):
            per_slot.setdefault(k, []).append((start + low * FRAME, end + low * FRAME, score))
        for k, word in per_slot.items():
            slot = slots[k]
            start, slot.end = densest(word, self.speech)
            slot.start = max(start, slot.end - longest(slot.text))
            slot.timed = True
            slot.score = sum(score for *_, score in word) / len(word)  # 2026-11-08
        return True

    def read(self, logp: np.ndarray, text: Text, low: int) -> list[Span] | None:
        """The letters' spans, strict or with the star the clip's prices allow, never on its
        silence for sure (asr/tolerated.py); None when the text cannot be read here."""
        if self.costs is None or not text.tokens or len(logp) < len(text.tokens):
            return token_spans(logp, text.tokens, text.bounds)
        spans = tolerant_spans(logp, text, self.costs, self.hard[low:low + len(logp)]).spans
        return None if None in spans else [s for s in spans if s is not None]
