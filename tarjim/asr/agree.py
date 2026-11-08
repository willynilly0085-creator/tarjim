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
from typing import Any

import numpy as np

from tarjim.asr.ctc import FRAME, Letters, token_spans
from tarjim.models import Word

SLACK = 0.5  # seconds of sound either side of a run's own time
RUN_GAP = 0.6  # seconds between two words that ends a run
RUN_WORDS = 12
FOUND = 0.3  # the mean likelihood of a run's letters that counts as said there

Tokens = Callable[[str], list[int]]
Score = Callable[[list[Word]], float | None]


def runs(words: list[Word]) -> list[list[Word]]:
    """The words in runs said in one breath by one speaker, none longer than RUN_WORDS."""
    found: list[list[Word]] = []
    for word in words:
        last = found[-1] if found else []
        if (last and word.start - last[-1].end <= RUN_GAP and word.speaker == last[-1].speaker
                and len(last) < RUN_WORDS):
            last.append(word)
        else:
            found.append([word])
    return found


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
    logp = emitter.emissions(wav)  # the whole clip's letters, heard once (asr/ctc.Letters)
    if isinstance(emitter.emissions, Letters):
        emitter.emissions.tell(wav)
    return lambda run: run_score(logp, run, engine.tokens)


def agreement(logp: np.ndarray, words: list[Word], tokens: Tokens) -> float | None:
    return share_found(lambda run: run_score(logp, run, tokens), words)


def share_found(score: Score, words: list[Word]) -> float | None:
    """The share of words found where they are timed; None when no word has letters to find."""
    found, counted = 0, 0
    for run in runs(words):
        score_of = score(run)
        if score_of is not None:
            counted += len(run)
            found += len(run) if score_of >= FOUND else 0
    return found / counted if counted else None
