"""One person, one voice (2026-11-25). In the owner's clip of Mark, Joanna Stern and Meta's
assistant, the listener split the assistant in two: 2.7 s of it became a fourth person, and two of
its lines were dubbed from that short sample, in a voice that changed mid-answer and was heard back
as English. A voice with too little speech to clone well, whose print is near one with enough, is
that person; its lines take their voice."""
from dataclasses import replace
from pathlib import Path

import numpy as np

from tarjim.dub.lines import Line

SHORT = 4.0  # seconds of sample: less clones poorly
ALIKE = 0.5  # the short sample was 0.62 alike the assistant's own, 0.30 alike Mark's


def prints(samples: dict[str, Path]) -> dict[str, tuple[float, np.ndarray]]:
    from tarjim.asr import voiceprint
    from tarjim.dub.audio import decode

    sounds = {who: decode(path, 1, voiceprint.RATE) for who, path in samples.items()}
    return {who: (len(sound) / voiceprint.RATE, voiceprint.print_of(sound))
            for who, sound in sounds.items()}


def moves(found: dict[str, tuple[float, np.ndarray]]) -> dict[str, str]:
    """Each short voice to the long one it sounds most like, when it sounds like one enough."""
    long = {who: vector for who, (seconds, vector) in found.items() if seconds >= SHORT}
    moved = {}
    for who, (seconds, vector) in found.items():
        alike = {other: float(vector @ print_) for other, print_ in long.items()}
        if seconds < SHORT and alike and max(alike.values()) >= ALIKE:
            moved[who] = max(alike, key=lambda other: alike[other])
    return moved


def merged(samples: dict[str, Path], lines: list[Line]) -> tuple[dict[str, Path], list[Line]]:
    """The samples and lines with every short voice handed to its person; as they were when the
    voice print model cannot be had (a print is no reason to fail a dub)."""
    from tarjim.asr import voiceprint

    try:
        moved = moves(prints(samples)) if voiceprint.fetched() else {}
    except Exception:
        moved = {}
    return ({who: path for who, path in samples.items() if who not in moved},
            [replace(line, speaker=moved.get(line.speaker, line.speaker)) for line in lines])
