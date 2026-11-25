"""The dubbed sound brought to the level X, TikTok and phones play videos at (2026-11-25). The
owner's dub of Mark and Joanna Stern came out at -26.7 LUFS, 4.4 dB under its own original, and
sounded faint beside every other video in the feed. The whole sound is measured, then raised by one
gain, with a limiter that only catches the peaks. ffmpeg's loudnorm, tried first, fell back to
riding the volume when a straight gain would clip, and lifted the breaths, word tails and pauses
about 7 dB nearer the voice: the owner heard it as whispering."""
import json
import math
import re
import subprocess
from pathlib import Path

from tarjim.media import source, tool

LOUDNESS = -14.0
PEAK = -1.5
LIMIT = round(10 ** (PEAK / 20), 3)
MOST = 15.0  # dB: a nearly silent sound is not raised into its own hiss
SECONDS = 600
MEASURE = f"loudnorm=I={LOUDNESS}:TP={PEAK}:print_format=json"
KEEP = "anull"
REPORT = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}")


def report(text: str) -> float | None:
    """The integrated loudness ffmpeg measured, or None for silence (-inf) or no report."""
    match = REPORT.search(text)
    try:
        found = float(json.loads(match.group())["input_i"]) if match else math.inf
    except (ValueError, KeyError):
        return None
    return found if math.isfinite(found) else None


def measured(sound: Path) -> float | None:
    try:
        result = subprocess.run([tool("ffmpeg"), "-hide_banner", "-nostats", *source(sound),
                                 "-af", MEASURE, "-f", "null", "-"],
                                capture_output=True, check=False, timeout=SECONDS)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    return report(result.stderr.decode("utf-8", "replace"))


def level(sound: Path) -> str:
    """One gain to the feed's level and a limiter for the peaks it pushes over. Sound that could
    not be measured stays as it is."""
    found = measured(sound)
    if found is None:
        return KEEP
    return f"volume={min(LOUDNESS - found, MOST):.2f}dB,alimiter=limit={LIMIT}:level=false"
