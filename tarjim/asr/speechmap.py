"""Where a clip is speech, said once per clip (2026-11-09): from the letters the aligner hears in
the whole clip once anyway (asr/letters.Letters) and one voice detector run, in three tiers.

- speech: the detector heard a voice, or the letters did (a run of letter mass at or above the
  clip's own threshold), so a chant the detector takes for silence is speech here;
- hard: neither did and the frames are blank-confident; a letter here pays the full penalty, as
  silence did before, music pauses included (no energy term: a loud bed is still silence);
- soft: everything else, a heard line over silence most of all. Before 2026-11-09 a heard line
  was speech outright, so a line stretched over silence made it free to place words on; now its
  letters pay a little there, so a stretched line never makes silence free and a chant the map
  misses is never banned. A heard line only ever turns hard into soft, never into speech.

The threshold is half the median letter mass where the detector heard speech (measured on the
bench on 2026-11-09: that median is 0.20 to 0.25 in speech on every clip, about 0.005 in pauses,
music beds' included, and the quantile rule first proposed found 6 s of a 31 s chant where this
finds all of it). With too little detected speech it is taken from the frames with letters in
them; with neither, a default. About 2 bytes a frame are kept (0.4 MB for two hours).
"""
from dataclasses import dataclass, replace
from itertools import pairwise
from typing import Any

import numpy as np

from tarjim.asr.ctc import BLANK, FRAME
from tarjim.asr.vad import SILENCE_PENALTY, speech_mask

HARD, SOFT, SPEECH = 0, 1, 2
SOFT_PENALTY = 2.0  # per frame, on letters: a heard line over silence
PENALTIES = np.array([SILENCE_PENALTY, SOFT_PENALTY, 0.0], dtype=np.float32)
SMOOTH = 5  # frames the letter mass is averaged over
RELATIVE = 0.5  # of the median letter mass in speech: the threshold
TAU_LOW, TAU_HIGH, TAU_DEFAULT = 0.05, 0.3, 0.1
FLOOR = 0.05  # letter mass that counts as letters heard, when the detector heard too little
CALIBRATE_S = 10.0  # seconds of speech the threshold is measured on
LEAST = 5  # frames in a run of letters that is speech
JOIN = round(0.15 / FRAME)  # frames between two runs that make them one

Span = tuple[float, float]


def spans_of(mask: np.ndarray) -> list[Span]:
    """The runs of True, in seconds."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return [(float(a * FRAME), float(b * FRAME)) for a, b in zip(edges[::2], edges[1::2],
                                                                 strict=True)]


def merged(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


@dataclass(frozen=True, eq=False)
class SpeechMap:
    vad: np.ndarray  # bool per frame: the detector's speech, padded (asr/vad.PAD)
    tier: np.ndarray  # int8 per frame: HARD, SOFT or SPEECH
    tau: float
    source: str  # "vad+ctc" | "ctc" | "ctc-uncalibrated" | "none"
    regions: tuple[Span, ...]  # the detector's speech, as it found it

    @property
    def frames(self) -> int:
        return len(self.tier)

    def ctc_only(self) -> list[Span]:
        """Speech the letters heard and the detector did not: chant, singing."""
        return spans_of((self.tier == SPEECH) & ~self.vad)

    def speech(self) -> list[Span]:
        """The detector's speech with what only the letters heard: what coverage checks."""
        return merged([*self.regions, *self.ctc_only()])

    def heard(self, spans: list[Span]) -> "SpeechMap":
        """Heard lines over hard silence make it soft, never speech."""
        tier = self.tier.copy()
        for start, end in spans:
            low, high = max(0, int(start / FRAME)), max(0, int(end / FRAME) + 1)
            tier[low:high][tier[low:high] == HARD] = SOFT
        return replace(self, tier=tier)

    def view(self, first: int, past: int) -> "SpeechMap":
        """A stretch of the clip from its frame `first` to before `past`, as asr/letters.Piece
        reads its letters; frames past the clip's end are soft."""
        extra = max(0, past - self.frames)
        tier = np.concatenate((self.tier[first:past], np.full(extra, SOFT, dtype=np.int8)))
        vad = np.concatenate((self.vad[first:past], np.zeros(extra, dtype=bool)))
        low, high = first * FRAME, past * FRAME
        shifted = tuple((a - low, b - low) for a, b in self.regions if b > low and a < high)
        return replace(self, tier=tier, vad=vad, regions=shifted)

    def penalty(self) -> np.ndarray:
        """Per frame, what a letter pays (asr/vad.mute)."""
        result: np.ndarray = PENALTIES[self.tier]
        return result

    def summary(self) -> dict[str, Any]:
        """As kept in speech.json: the tiers run by run, and the spans a person can read."""
        edges = np.flatnonzero(np.diff(self.tier)) + 1
        starts = np.concatenate(([0], edges))
        counts = np.diff(np.concatenate((starts, [self.frames])))
        return {"source": self.source, "tau": self.tau, "frames": self.frames,
                "vad": [list(r) for r in self.regions],
                "speech": [[round(a, 2), round(b, 2)] for a, b in self.speech()],
                "ctc_only": [[round(a, 2), round(b, 2)] for a, b in self.ctc_only()],
                "tiers": [[int(self.tier[s]), int(n)] for s, n in zip(starts, counts,
                                                                    strict=True)]}


def restored(data: dict[str, Any]) -> SpeechMap:
    """A map from its summary."""
    tiers = np.array(data["tiers"], dtype=np.int64).reshape(-1, 2)
    tier = np.repeat(tiers[:, 0], tiers[:, 1]).astype(np.int8)
    regions = tuple((float(a), float(b)) for a, b in data["vad"])
    vad = speech_mask(list(regions), len(tier))[:len(tier)]
    return SpeechMap(vad, tier, float(data["tau"]), str(data["source"]), regions)


def mass(logp: np.ndarray | None, frames: int) -> np.ndarray:
    """Per frame, how likely a letter rather than a blank is, averaged over SMOOTH frames."""
    found = np.zeros(frames, dtype=np.float32)
    if logp is not None and len(logp):
        letters = 1.0 - np.exp(logp[:frames, BLANK].astype(np.float64))
        found[:len(letters)] = np.convolve(letters, np.ones(SMOOTH) / SMOOTH, "same")
    return found


def threshold(nonblank: np.ndarray, vad: np.ndarray, heard: bool) -> tuple[float, str]:
    """The clip's own letter-mass threshold and what it was measured on."""
    if not heard:
        return TAU_DEFAULT, "none"
    least = CALIBRATE_S / FRAME
    for reference, source in ((nonblank[vad], "vad+ctc"), (nonblank[nonblank >= FLOOR], "ctc")):
        if len(reference) >= least:
            tau = RELATIVE * float(np.median(reference))
            return float(np.clip(tau, TAU_LOW, TAU_HIGH)), source
    return TAU_DEFAULT, "ctc-uncalibrated"


def runs(mask: np.ndarray) -> np.ndarray:
    """The runs of at least LEAST frames, those JOIN frames apart or less made one."""
    kept = np.zeros_like(mask)
    for start, end in spans_of(mask):
        low, high = round(start / FRAME), round(end / FRAME)
        kept[low:high] = high - low >= LEAST
    found = spans_of(kept)
    for (_, end), (start, _) in pairwise(found):
        low, high = round(end / FRAME), round(start / FRAME)
        kept[low:high] = high - low <= JOIN
    return kept


def build(logp: np.ndarray | None, frames: int, regions: list[Span]) -> SpeechMap:
    """The map of a sound of `frames` frames from its letters (None: a stand-in aligner) and the
    detector's speech."""
    vad = speech_mask(regions, frames)[:frames]
    nonblank = mass(logp, frames)
    tau, source = threshold(nonblank, vad, logp is not None)
    speech = vad | runs(nonblank >= tau)
    tier = np.where(speech, SPEECH, np.where(nonblank < tau / 2, HARD, SOFT)).astype(np.int8)
    return SpeechMap(vad, tier, tau, source, tuple(regions))
