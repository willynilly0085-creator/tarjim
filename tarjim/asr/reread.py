"""A weak stretch read again with the skip on (asr/weak.Window, asr/tolerated.mended), so a word
the sound does not hold there is left out instead of squeezed in (2026-11-09).

A window of a copy reads its speaker's words alone; the other voices' words stay where they are
and the frames they were found on are made silence for the reading (asr/vad.mute), so the copy
can neither take another voice's line of the same words nor its sound (the review of
2026-11-09: on en_refrain_twice x loop_all S1's copy was timed onto S2's speech of its words).
Moved here from asr/tolerated.py on 2026-11-09.
"""
from bisect import bisect_right
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from tarjim.asr.ctc import FRAME, Span
from tarjim.asr.groups import densest
from tarjim.asr.numbers import said
from tarjim.asr.spread import longest
from tarjim.asr.tolerant import Text, tolerant_spans
from tarjim.asr.unplaced import Lines, all_copies
from tarjim.asr.vad import SILENCE_PENALTY, mute
from tarjim.asr.weak import Window
from tarjim.models import Word

if TYPE_CHECKING:
    from tarjim.asr.align import AlignEngine
    from tarjim.asr.tolerated import Heard


def inside(words: list[Word], window: Window) -> list[int]:
    """The aligned words inside the window, of its speaker alone for a copy's."""
    return [i for i, w in enumerate(words) if w.source == "aligned"
            and window.low <= w.start and w.end <= window.high
            and window.speaker in (None, w.speaker)]


def letters_of(engine: "AlignEngine", words: list[Word], window: Window,
               aside: frozenset[int]) -> dict[int, list[int]]:
    """The words read again that have letters, with them, in the lines' order as the first
    reading had them, a reply said over a turn (`aside`) put in by its time as the words are
    shown (asr/fuse.slotted): sorted by time, two voices at once were read one word of each
    after the other (2026-11-09)."""
    found = inside(words, window)
    kept = [i for i in found if i not in aside]
    for i in (i for i in found if i in aside):
        kept.insert(bisect_right([words[j].start for j in kept], words[i].start), i)
    spoken = said([words[i].text for i in kept], engine.language)
    letters = {i: engine.tokens(s) for i, s in zip(kept, spoken, strict=True)}
    return {i: tokens for i, tokens in letters.items() if tokens}


def others_muted(logp: np.ndarray, words: list[Word], window: Window, first: int) -> np.ndarray:
    """The window's letters, the frames another voice's words were found on made silence when
    a copy's speaker is read alone."""
    if window.speaker is None:
        return logp
    penalty = np.zeros(len(logp), dtype=np.float32)
    for w in words:
        if w.source == "aligned" and w.speaker != window.speaker:
            low, high = int(w.start / FRAME) - first, int(w.end / FRAME) + 1 - first
            penalty[max(0, low):max(0, high)] = SILENCE_PENALTY
    return mute(logp, penalty) if penalty.any() else logp


def reread(engine: "AlignEngine", heard: "Heard", words: list[Word], window: Window) -> set[int]:
    """The window read again with the skip on; when it left words out, the others take their
    new times. The indices left out."""
    letters = letters_of(engine, words, window, heard.aside)
    first = max(0, int(window.low / FRAME))
    past = min(len(heard.logp), int(window.high / FRAME) + 1)
    tokens = [t for found in letters.values() for t in found]
    costs = engine.calibration.costs if engine.calibration else None
    if costs is None or not tokens or past - first < len(tokens):
        return set()
    text = Text(tokens, [k for k, found in enumerate(letters.values()) for _ in found])
    sound = others_muted(heard.logp[first:past], words, window, first)
    read = tolerant_spans(sound, text, replace(costs, skip=True), engine.hard[first:past])
    indices = list(letters)
    left = {indices[k] for k, placed in enumerate(read.placed) if not placed}
    if window.copies and not all_copies(words, left, Lines(heard.lines, heard.speech)):
        return set()  # said over another speaker: only a copy is left out (asr/weak.py)
    if left:
        timed(engine, words, read_spans(read.spans, text, indices, first), left)
    return left


def read_spans(spans: list[Span | None], text: Text, indices: list[int],
               first: int) -> dict[int, list[Span]]:
    """Each word's letters' spans in the sound's own seconds, by the word's index."""
    per_word: dict[int, list[Span]] = {}
    for k, span in enumerate(spans):
        if span is not None:
            start, end, score = span
            per_word.setdefault(indices[text.word_of[k]], []).append(
                (start + first * FRAME, end + first * FRAME, score))
    return per_word


def timed(engine: "AlignEngine", words: list[Word], spans: dict[int, list[Span]],
          left: set[int]) -> None:
    """The words read again take their new times, as AlignEngine.time_slots gives them; those
    left out are marked unplaced."""
    for index, found in spans.items():
        start, end = densest(found, engine.speech)
        words[index] = replace(words[index], start=max(start, end - longest(words[index].text)),
                               end=end, score=sum(s for *_, s in found) / len(found))
    for index in left:
        words[index] = replace(words[index], source="unplaced")
