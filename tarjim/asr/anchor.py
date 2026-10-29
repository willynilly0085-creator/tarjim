"""Utterance times corrected by the words this computer heard, before the words are aligned.

A cloud listener's times can drift. On 2026-10-29 all three Gemini passes placed the last 20
seconds of a 4-minute clip up to 9.5 seconds early; the aligner searches only near the times it
is given, so it squashed that speech before it was said and left the last 8 seconds of talk with
no subtitles. The local listener's word times come from the audio itself: each utterance moves to
where its own words were heard, when enough of them match. An utterance too short to match ("Mhm",
"Right") moves with its nearest matched neighbour, since drift builds up over a stretch.
"""
from difflib import SequenceMatcher
from statistics import median

from tarjim.asr.align import proportional
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word

DRIFT = 2.0  # smaller differences are the aligner's to settle (it searches a second either side)
SHARE = 0.5  # of an utterance's words, heard in the same order by the local listener
LEAST = 2
RUN = 2  # matched words must come in runs: a lone "okay" can match the wrong one
REACH = 15.0  # a short utterance follows a matched neighbour this close


def shifts(utterances: list[Utterance], heard: list[Word]) -> dict[int, list[float]]:
    mine = [(k, w) for k, u in enumerate(utterances) for w in proportional(u)]
    matcher = SequenceMatcher(None, [norm(w.text) for _, w in mine],
                              [norm(w.text) for w in heard], autojunk=False)
    found: dict[int, list[float]] = {}
    for a, b, size in matcher.get_matching_blocks():
        for step in range(size if size >= RUN else 0):
            owner, word = mine[a + step]
            found.setdefault(owner, []).append(heard[b + step].start - word.start)
    return found


def own_delta(utterance: Utterance, found: list[float]) -> float | None:
    if len(found) < max(LEAST, SHARE * len(utterance.text.split())):
        return None
    return median(found)


def borrowed(index: int, utterances: list[Utterance], deltas: list[float | None]) -> float:
    known = [(abs(utterances[k].start - utterances[index].start), d)
             for k, d in enumerate(deltas) if d is not None]
    near = [(gap, d) for gap, d in known if gap <= REACH]
    return min(near)[1] if near else 0.0


def moved(utterance: Utterance, delta: float, duration: float) -> Utterance:
    if abs(delta) < DRIFT:
        return utterance
    start = min(max(0.0, utterance.start + delta), duration)
    end = min(max(start, utterance.end + delta), duration)
    return Utterance(start, end, utterance.speaker, utterance.text)


def anchor(utterances: list[Utterance], heard: list[Word], duration: float) -> list[Utterance]:
    if not heard:
        return utterances
    found = shifts(utterances, heard)
    deltas = [own_delta(u, found.get(k, [])) for k, u in enumerate(utterances)]
    return [moved(u, d if d is not None else borrowed(k, utterances, deltas), duration)
            for k, (u, d) in enumerate(zip(utterances, deltas, strict=True))]
