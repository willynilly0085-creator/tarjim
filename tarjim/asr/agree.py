"""Whether the words are said at the times they were given, checked by listening once more.

The aligner hears letters (asr/ctc.py). Each run of words that follow one another closely is
looked for in the sound from just before its first word to just after its last, its letters alone
and in order: where the words are said there, the aligner finds their letters with a high
likelihood; where the timing went wrong (the words sit on other speech, on music or on silence),
it does not. The share of words whose run is found says how far the subtitles can be trusted to
show with the voice. A run placed on silence is not found either: its letters are not there.
The voice detector is not asked, since it takes chanting and singing for silence.
"""
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import numpy as np

from tarjim.asr.ctc import FRAME, token_spans
from tarjim.models import Word

SLACK = 0.5  # seconds of sound either side of a run's own time
RUN_GAP = 0.6  # seconds between two words that ends a run
RUN_WORDS = 12
FOUND = 0.3  # the mean likelihood of a run's letters that counts as said there

Tokens = Callable[[str], list[int]]
Score = Callable[[list[Word]], float | None]


def run_spans(words: list[Word]) -> list[tuple[int, int]]:
    """Where each run said in one breath by one speaker begins and ends, as (first, past)."""
    found: list[tuple[int, int]] = []
    for index, word in enumerate(words):
        first = found[-1][0] if found else 0
        last = words[index - 1] if index else None
        if (last is not None and word.start - last.end <= RUN_GAP
                and word.speaker == last.speaker and index - first < RUN_WORDS):
            found[-1] = (first, index + 1)
        else:
            found.append((index, index + 1))
    return found


def runs(words: list[Word]) -> list[list[Word]]:
    """The words in runs said in one breath by one speaker, none longer than RUN_WORDS."""
    return [words[first:past] for first, past in run_spans(words)]


def run_score(logp: np.ndarray, run: list[Word], tokens: Tokens) -> float | None:
    """How likely the run's letters are in its own stretch of sound; None for no letters."""
    letters = [t for word in run for t in tokens(word.text)]
    if not letters:
        return None
    low = max(0, int((run[0].start - SLACK) / FRAME))
    high = min(len(logp), int((run[-1].end + SLACK) / FRAME) + 1)
    spans = token_spans(logp[low:high], letters)
    return 0.0 if spans is None else float(np.mean([score for *_, score in spans]))


def scorer(engine: Any, wav: Any) -> Score | None:
    """How likely a run is said where it is timed, by the aligner's own ears; None for a
    stand-in aligner with none."""
    emitter = getattr(engine, "emitter", None)
    if emitter is None:
        return None
    logp = emitter.emissions(wav)  # the whole clip's letters, heard once (asr/letters.Letters)
    return lambda run: run_score(logp, run, engine.tokens)


def agreement(logp: np.ndarray, words: list[Word], tokens: Tokens) -> float | None:
    return share_found(lambda run: run_score(logp, run, tokens), words)


def scored(words: list[Word], score: Score) -> list[Word]:
    """Each word with its run's strict score (None for a run with no letters), so what reads
    the words later finds it there and nothing is decoded again (2026-11-09)."""
    found: list[Word] = []
    for first, past in run_spans(words):
        value = score(words[first:past])
        found += [replace(w, score=value) for w in words[first:past]]
    return found


def share_scored(words: list[Word]) -> float | None:
    """share_found read from the scores `scored` gave the words."""
    counted = [w.score for w in words if w.score is not None]
    return sum(s >= FOUND for s in counted) / len(counted) if counted else None


def clip_baseline(scores: list[float]) -> float:
    """The clip's own floor for a run found where it is timed: FOUND, or half the clip's median
    run score when that is lower (two voices at once, a hoarse voice), so a whole clip whose
    letters are faint is not taken for one timed wrong throughout (2026-11-09)."""
    return min(FOUND, 0.5 * float(np.median(scores))) if scores else FOUND


def share_found(score: Score, words: list[Word]) -> float | None:
    """The share of words found where they are timed; None when no word has letters to find."""
    found, counted = 0, 0
    for run in runs(words):
        score_of = score(run)
        if score_of is not None:
            counted += len(run)
            found += len(run) if score_of >= FOUND else 0
    return found / counted if counted else None
