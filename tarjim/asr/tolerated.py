"""The aligner's tolerant mode (listen.aligner 'tolerant', 2026-11-09): what it adds to the strict
reading in asr/align.py.

Once per clip its prices are measured (asr/costs.calibrated) on a strict reading of its densest
stretches, a minute at most (asr/groups.sample), with the clip's floor for a run said where it
is timed (agree.clip_baseline). Every group is then read with the star on, so sound the text
does not hold passes instead of dragging the words beside it, never on silence for sure (the
speech map's hard tier).

Then each run of words whose strict score is under the floor, and that is not said over another
speaker's line (two voices at once score low and prove nothing), is read again with the skip on
from AROUND seconds before it to AROUND after: a word the sound does not hold there is left out
instead of squeezed in, and goes to asr/unplaced.py. When nothing there is left out the first
times stay. With too few runs measured there are no prices and the reading stays strict.
"""
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import numpy as np

from tarjim.asr.agree import SLACK, clip_baseline, run_score, run_spans
from tarjim.asr.costs import Calibration, Calibrations, Run, calibrated
from tarjim.asr.ctc import FRAME, Span
from tarjim.asr.groups import densest, sample
from tarjim.asr.letters import Piece, fingerprint
from tarjim.asr.numbers import said
from tarjim.asr.speechmap import SpeechMap, build
from tarjim.asr.spread import longest
from tarjim.asr.tolerant import Text, tolerant_spans
from tarjim.asr.unplaced import Lines, settled
from tarjim.asr.vad import mute
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

if TYPE_CHECKING:
    from tarjim.asr.align import AlignEngine

STRICT, TOLERANT = "strict", "tolerant"
AROUND = 2.0  # seconds either side of a run read again with the skip on

Window = tuple[float, float, str]  # from, to (seconds) and the speaker whose words are read


@dataclass(frozen=True)
class Heard:
    raw: np.ndarray  # the letters as heard: what a run's strict score is read from
    logp: np.ndarray  # with the speech map's penalties: what words are placed by
    speech: list[tuple[float, float]]  # the map's speech, in the sound's own seconds


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
    """The sound's letters as heard and as the words are placed by, and its map. The heard
    lines over silence are soft, not speech: a line stretched over silence no longer makes it
    free, and a chant the detector misses is speech by its letters (asr/speechmap.py,
    2026-11-09; before, every heard line was speech outright). A word is still not cut at a
    soft frame (groups.densest): on the bench, cutting there moved a word off its speech in two
    clips and helped none."""
    view = mapped(wav, raw, speech).heard([(u.start, u.end) for u in utterances])
    return Heard(raw, mute(raw, view.penalty()), view.speech()), view


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
    evened = len(engine.evened)
    words = [w for group in sample(turns) for w in engine.align_group(heard.logp, group)]
    del engine.evened[evened:]  # read only to measure: not told
    aligned = [w for w in words if w.source == "aligned"]
    found = [aligned[first:past] for first, past in run_spans(aligned)]
    scores = [run_score(heard.raw, run, engine.tokens) for run in found]
    return Calibration(calibrated(heard.raw, [ran(engine, heard.raw, run) for run in found]),
                       clip_baseline([s for s in scores if s is not None]))


def ran(engine: "AlignEngine", raw: np.ndarray, run: list[Word]) -> Run:
    """A run's letters and frames, as agree.run_score reads them."""
    low = max(0, int((run[0].start - SLACK) / FRAME))
    high = min(len(raw), int((run[-1].end + SLACK) / FRAME) + 1)
    return Run([t for w in run for t in engine.tokens(w.text)], low, high)


def mended(engine: "AlignEngine", heard: Heard, lines: list[Utterance],
           words: list[Word]) -> list[Word]:
    """The words with the weak runs read again with the skip on, and what that left out
    dropped as a copy or spread and marked (asr/unplaced.py)."""
    words, left = list(words), set[int]()
    for window in weak(engine, heard, lines, words):
        left |= reread(engine, heard, words, window)
    outcome = settled(words, left, Lines(lines, heard.speech))
    engine.dropped, engine.unplaced = outcome.dropped, outcome.regions
    return outcome.words


def over_another(run: list[Word], lines: list[Utterance]) -> bool:
    who, start, end = run[0].speaker, run[0].start, run[-1].end
    return any(u.speaker != who and u.start < end and u.end > start for u in lines)


def weak(engine: "AlignEngine", heard: Heard, lines: list[Utterance],
         words: list[Word]) -> list[Window]:
    """Around each run under the clip's floor not said over another speaker, one speaker's
    stretches that meet made one."""
    floor = engine.calibration.baseline if engine.calibration else 0.0
    found: list[Window] = []
    for first, past in run_spans(words):
        run = words[first:past]
        score = run_score(heard.raw, run, engine.tokens)
        if score is None or score >= floor or over_another(run, lines):
            continue
        low, high, who = run[0].start - AROUND, run[-1].end + AROUND, run[0].speaker
        if found and found[-1][2] == who and low <= found[-1][1]:
            found[-1] = (found[-1][0], high, who)
        else:
            found.append((low, high, who))
    return found


def letters_of(engine: "AlignEngine", words: list[Word], window: Window) -> dict[int, list[int]]:
    """The aligned words of the window's speaker inside it that have letters, with them."""
    low, high, who = window
    inside = [i for i, w in enumerate(words) if w.speaker == who and w.source == "aligned"
              and low <= w.start and w.end <= high]
    spoken = said([words[i].text for i in inside], engine.language)
    letters = {i: engine.tokens(s) for i, s in zip(inside, spoken, strict=True)}
    return {i: tokens for i, tokens in letters.items() if tokens}


def reread(engine: "AlignEngine", heard: Heard, words: list[Word], window: Window) -> set[int]:
    """The window read again with the skip on; when it left words out, the others take their
    new times. The indices left out."""
    letters = letters_of(engine, words, window)
    first = max(0, int(window[0] / FRAME))
    past = min(len(heard.logp), int(window[1] / FRAME) + 1)
    tokens = [t for found in letters.values() for t in found]
    costs = engine.calibration.costs if engine.calibration else None
    if costs is None or not tokens or past - first < len(tokens):
        return set()
    text = Text(tokens, [k for k, found in enumerate(letters.values()) for _ in found])
    read = tolerant_spans(heard.logp[first:past], text, replace(costs, skip=True),
                          engine.hard[first:past])
    indices = list(letters)
    left = {indices[k] for k, placed in enumerate(read.placed) if not placed}
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
