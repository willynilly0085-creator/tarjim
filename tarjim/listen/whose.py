"""Each line's speaker, checked against the voice heard in it.

The cloud listener names speakers by what it hears, and it can swap them: on 2026-11-06 an
interview had host and guest swapped after a two-second pause, in all three listenings, so from
there on each one wore the other's colour. Here every line long enough to know a voice by gets a
voice print (asr/voiceprint.py), each speaker the average print of their lines, and a line whose
voice is clearly another speaker's, by MARGIN or more, is given to that speaker. Only speakers of
one piece of a long video are compared (speakers.py), lines too short to know a voice by keep
their label, and one speaker is never checked against nobody: the labels are corrected, never
invented.
"""
from dataclasses import replace
from typing import Any

import numpy as np

from tarjim.asr.voiceprint import RATE
from tarjim.models import Word
from tarjim.speakers import who

SHORTEST = 0.8  # seconds: a shorter line says too little to know the voice by
STEADY = 1.5  # seconds: lines this long make up a speaker's average print
GAP = 1.0  # seconds of silence that end a line even with the same speaker
MARGIN = 0.15  # how much closer another speaker's voice must be to take the line
NEAREST = 0.4  # how close that voice must be at least
FEWEST = 2  # speakers: one is never checked against nobody

Line = tuple[int, int]  # the first word and the one past the last


def lines(words: list[Word]) -> list[Line]:
    found: list[Line] = []
    for k, word in enumerate(words):
        if found and who(words[k - 1].speaker) == who(word.speaker) and (
                word.start - words[k - 1].end <= GAP):
            found[-1] = (found[-1][0], k + 1)
        else:
            found.append((k, k + 1))
    return found


def span(words: list[Word], line: Line) -> tuple[float, float]:
    return words[line[0]].start, words[line[1] - 1].end


def piece(label: str) -> str:
    return who(label).rpartition(".")[0]


def length(words: list[Word], line: Line) -> float:
    start, end = span(words, line)
    return end - start


def averages(prints: dict[Line, np.ndarray], words: list[Word]) -> dict[str, np.ndarray]:
    """Each speaker's print over their steady lines, or over all their lines when none is."""
    found: dict[str, list[np.ndarray]] = {}
    steady: dict[str, list[np.ndarray]] = {}
    for line, voice in prints.items():
        name = who(words[line[0]].speaker)
        found.setdefault(name, []).append(voice)
        if length(words, line) >= STEADY:
            steady.setdefault(name, []).append(voice)
    return {name: np.mean(steady.get(name) or voices, axis=0) for name, voices in found.items()}


def nearer(voice: np.ndarray, own: str, known: dict[str, np.ndarray]) -> str:
    """Another speaker of the same piece whose voice this clearly is, or own."""
    rivals = {name: float(voice @ v / np.linalg.norm(v)) for name, v in known.items()
              if piece(name) == piece(own)}
    best = max(rivals, key=lambda name: rivals[name])
    mine = rivals.get(own, -1.0)
    return best if rivals[best] >= NEAREST and rivals[best] - mine >= MARGIN else own


def printed(words: list[Word], wav: Any) -> dict[Line, np.ndarray]:
    from tarjim.asr.voiceprint import print_of

    found = {}
    for line in lines(words):
        start, end = span(words, line)
        if end - start >= SHORTEST and words[line[0]].speaker:
            found[line] = print_of(wav[int(start * RATE):int(end * RATE)])
    return found


def checked(words: list[Word], wav: Any) -> list[Word]:
    """The words with each line given to the speaker whose voice it is."""
    prints = printed(words, wav)
    known = averages(prints, words)
    if len(known) < FEWEST:
        return words
    moved, out = 0, list(words)
    for line, voice in prints.items():
        own = who(words[line[0]].speaker)
        voice_of = nearer(voice, own, known)
        if voice_of != own:
            moved += 1
            out[line[0]:line[1]] = [replace(w, speaker=voice_of) for w in out[line[0]:line[1]]]
    print(f"speakers: {len(prints)} lines checked by voice, {moved} given to another speaker",
          flush=True)
    return out


def by_voice(words: list[Word], wav: Any) -> list[Word]:
    """The checked words, or the words as they are when no voice print can be made here."""
    from tarjim.asr.voiceprint import fetched

    if len({who(w.speaker) for w in words if w.speaker}) < FEWEST or not fetched():
        return words
    try:
        return checked(words, wav)
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        print(f"speakers: the voice check did not run: {str(error)[:200]}", flush=True)
        return words
