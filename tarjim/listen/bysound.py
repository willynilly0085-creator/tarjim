"""What the clip's speech map (asr/speechmap.py) says of a stretch no line covers (2026-11-09).

A stretch is a gap by the map's own speech, padded as the aligner reads it (asr/vad.PAD), whether
the listener on this computer ran or not: on 2026-11-09 a 1.9 s stretch of the detector's speech
(2.1 s padded) became a gap only when the local words stretched it to 2.0 s, so the same clip lost
it with the local listener off. One the local words alone make a gap is judged by the frames
outside the map's speech: given up (listed, never asked about) when nearly all of them are silent
to the letters too. Judged by the share the map called speech, which outside its speech is about
none, every such stretch was given up, quiet speech the letters partly heard (the soft tier) too.
"""
import numpy as np

from tarjim.asr.ctc import FRAME
from tarjim.asr.speechmap import HARD, SPEECH, SpeechMap
from tarjim.asr.vad import PAD

Span = tuple[float, float]

# Of the frames only the local words call speech, the share the letters must not call silent
# (asr/speechmap.HARD) for the sound to hold speech there (2026-11-09); the share is logged
NO_SPEECH = 0.3
NO_SOUND = "the sound holds no speech"
SOUNDED = "the sound holds speech"
UNCHECKED = "only local words call it speech: not checked against the sound (no letters heard)"


def frames_of(frames: int, spans: list[Span], pad: float = 0.0) -> np.ndarray:
    """Per frame of the map, whether it lies in one of the spans, each widened by `pad`."""
    mask = np.zeros(frames, dtype=bool)
    for a, b in spans:
        first = max(round((a - pad) / FRAME), 0)
        mask[first:max(round((b + pad) / FRAME), first + 1)] = True
    return mask


def judged(speech_map: SpeechMap, rest: np.ndarray) -> str:
    """What the frames only local words call speech hold. A map with no letters heard is the
    detector's alone, which takes a chant for silence, so it does not judge."""
    if speech_map.source == "none":
        return UNCHECKED
    share = float(np.mean(rest != HARD)) if len(rest) else 0.0
    return f"{NO_SOUND if share < NO_SPEECH else SOUNDED} ({share:.0%} of it not silent)"


def by_sound(speech_map: SpeechMap, group: list[Span], covered: list[Span],
             shortest: float) -> tuple[str, float]:
    """The seconds of the map's speech in a stretch, its pad in and the lines' times out, and what
    the sound says of it: nothing when that speech alone makes it a gap (speech by construction),
    else the judgement of the frames only the local words call speech. The stretch's own times
    stay unpadded, so no word is placed in the pad (listen/wordcover.spread)."""
    speech = speech_map.tier == SPEECH
    frames = len(speech)
    padded = frames_of(frames, group, PAD) & ~frames_of(frames, covered)
    mapped = FRAME * int(np.count_nonzero(padded & speech))
    if mapped >= shortest:
        return "", mapped
    inside = frames_of(frames, group) & ~speech
    return judged(speech_map, speech_map.tier[inside]), mapped
