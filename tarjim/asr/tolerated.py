"""The aligner's tolerant mode (listen.aligner 'tolerant', 2026-11-09): what it adds to the strict
reading in asr/align.py.

Once per clip its prices are measured (asr/costs.calibrated) on a strict reading of its densest
stretches, a minute at most (asr/groups.sample), with the clip's floor for a run said where it
is timed (agree.clip_baseline). Every group is then read with the star on, so sound the text
does not hold passes instead of dragging the words beside it, never on silence for sure (the
speech map's hard tier).

Then each run of words whose strict score is under the floor (asr/weak.py says which) is read
again with the skip on: a word the sound does not hold there is left out instead of squeezed in,
and goes to asr/unplaced.py. When nothing there is left out the first times stay. With too few
runs measured, or a clip much of whose speech its letters alone hear (a chant: asr/costs.SUNG),
there are no prices and the reading stays strict.
"""
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import numpy as np

from tarjim.asr.agree import SLACK, clip_baseline, run_score, run_spans
from tarjim.asr.costs import SUNG, Calibration, Calibrations, Run, calibrated
from tarjim.asr.ctc import FRAME
from tarjim.asr.groups import sample
from tarjim.asr.letters import Piece, fingerprint
from tarjim.asr.reread import reread
from tarjim.asr.speechmap import SpeechMap, build
from tarjim.asr.unplaced import Lines, owners, settled
from tarjim.asr.vad import mute
from tarjim.asr.weak import Weak
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

if TYPE_CHECKING:
    from tarjim.asr.align import AlignEngine

STRICT, TOLERANT = "strict", "tolerant"


@dataclass(frozen=True)
class Heard:
    raw: np.ndarray  # the letters as heard: what a run's strict score is read from
    logp: np.ndarray  # with the speech map's penalties: what words are placed by
    speech: list[tuple[float, float]]  # the map's speech, in the sound's own seconds
    lines: list[Utterance]  # the lines aligned in it
    aside: frozenset[int] = frozenset()  # words of replies said over a turn
    sung: float = 0.0  # the share of the clip's speech its letters alone hear (asr/costs.SUNG)


def mapped(wav: Any, logp: np.ndarray, speech: SpeechMap | None) -> SpeechMap:
    """The sound's part of the clip's speech map; with none (a dub's lines, 2026-11-09), the
    sound's own, the voice detector run on it. Moved here from asr/align.py on 2026-11-09."""
    first = wav.first if isinstance(wav, Piece) else 0
    if speech is not None:
        return speech.view(first, first + len(logp))
    from tarjim.asr.vad import speech_regions

    return build(logp, len(logp), speech_regions(wav))


def heard_in(wav: Any, raw: np.ndarray, speech: SpeechMap | None,
             utterances: list[Utterance]) -> tuple[Heard, SpeechMap]:
    """The sound's letters as heard and as the words are placed by, and its map, the heard lines
    over silence soft, not speech (asr/speechmap.py; moved here from asr/align.py, 2026-11-09).
    A word is still not cut at a soft frame (groups.densest): on the bench, cutting there moved
    a word off its speech in two clips and helped none."""
    view = mapped(wav, raw, speech).heard([(u.start, u.end) for u in utterances])
    sung = (speech if speech is not None else view).sung()
    return Heard(raw, mute(raw, view.penalty()), view.speech(), utterances, sung=sung), view


def mode() -> str:
    from tarjim.prefs.active import active

    return str(active().listen.aligner)


def priced(engine: "AlignEngine", wav: Any, heard: Heard,
           turns: list[Utterance]) -> Calibration | None:
    """The clip's calibration in the tolerant mode, measured on its first timing and kept for
    the rest; None in the strict mode."""
    if mode() != TOLERANT or not turns:
        return None
    kept = getattr(engine, "calibrations", None) or Calibrations()
    engine.calibrations = kept
    clip = wav.clip if isinstance(wav, Piece) else wav
    return kept(fingerprint(clip), lambda: measured(engine, heard, turns))


def measured(engine: "AlignEngine", heard: Heard, turns: list[Utterance]) -> Calibration:
    """The densest stretches read strictly, their runs' letters and scores measured. A clip
    much of whose speech its letters alone hear is read strictly and nothing is measured:
    the reading would cost a weak CPU time for prices not used (2026-11-09)."""
    if heard.sung >= SUNG:
        made = Calibration(None, 0.0)
        told(None, made, heard.sung)
        return made
    evened = len(engine.evened)
    words = [w for group in sample(turns) for w in engine.align_group(heard.logp, group)]
    del engine.evened[evened:]  # read only to measure: not told
    aligned = [w for w in words if w.source == "aligned"]
    found = [aligned[first:past] for first, past in run_spans(aligned)]
    scores = [run_score(heard.raw, run, engine.tokens) for run in found]
    costs = calibrated(heard.raw, [ran(engine, heard.raw, r) for r in found])
    made = Calibration(costs, clip_baseline([s for s in scores if s is not None]))
    told(len(found), made, None)
    return made


def told(runs: int | None, made: Calibration, sung: float | None) -> None:
    star = made.costs.star_delta if made.costs else None
    print("aligner: tolerant, " + (
        f"{sung:.0%} of the speech heard by its letters alone (a chant, singing), read strictly"
        if sung is not None else f"measured on {runs} runs: " + (
            "too few found, read strictly" if star is None else
            f"what the text does not hold passes {star:.1f} below the loudest letter")),
          flush=True)


def ran(engine: "AlignEngine", raw: np.ndarray, run: list[Word]) -> Run:
    """A run's letters and frames, as agree.run_score reads them."""
    low = max(0, int((run[0].start - SLACK) / FRAME))
    high = min(len(raw), int((run[-1].end + SLACK) / FRAME) + 1)
    return Run([t for w in run for t in engine.tokens(w.text)], low, high)


def mended(engine: "AlignEngine", heard: Heard, words: list[Word]) -> list[Word]:
    """The words with the weak runs read again with the skip on, and what that left out
    dropped as a copy or spread and marked (asr/unplaced.py)."""
    from tarjim.asr.align import overlapping

    words, left, over = list(words), set[int](), overlapping(heard.lines)
    heard = replace(heard, aside=frozenset(i for i, k in enumerate(owners(heard.lines))
                                           if k < len(over) and over[k]))
    floor = engine.calibration.baseline if engine.calibration else 0.0
    for window in Weak(words, heard.lines, floor).windows(
            lambda run: run_score(heard.raw, run, engine.tokens)):
        left |= reread(engine, heard, words, window)
    outcome = settled(words, left, Lines(heard.lines, heard.speech))
    engine.dropped, engine.unplaced = outcome.dropped | outcome.unheard, outcome.regions
    return outcome.words
