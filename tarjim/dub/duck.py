"""The background brought down under the people's words (2026-11-25). Separating the voices from
the background leaves a trace of the original speech in it: in the owner's clip of Mark and Joanna
Stern the background's speech band (1-4 kHz) was 16 dB stronger while they talked than while they
were silent, and once the dub was raised to the feed's level it was heard as whispering under the
new voice. Between the lines the music and the room stay as they are, and so do the people's own
sounds that have no words to translate, a laugh or a sigh: the owner missed the laughs at the end
of his clip, which went with the rest of the original voices."""
import numpy as np

from tarjim.dub.audio import RATE
from tarjim.dub.lines import Line
from tarjim.dub.separate import Stems

DUCK = 0.2  # about -14 dB: at -10 dB the speech band still stood 7.8 dB over the quiet
RAMP = 0.15


def talking(lines: list[Line], length: int) -> np.ndarray:
    """1 while someone says a line, 0 between, with a RAMP-long slope either side."""
    said = np.zeros(length, dtype=np.float32)
    edge = int(RAMP * RATE)
    for line in lines:
        start = max(int(line.start * RATE) - edge // 2, 0)
        said[start:int((line.start + line.talk) * RATE) + edge // 2] = 1.0
    smooth: np.ndarray = np.convolve(said, np.full(edge, 1 / edge, dtype=np.float32), mode="same")
    return smooth


def envelope(lines: list[Line], length: int) -> np.ndarray:
    """1 where nobody talks, DUCK while someone does."""
    found: np.ndarray = 1.0 - (1.0 - DUCK) * talking(lines, length)
    return found


def under_voices(stems: Stems, lines: list[Line]) -> np.ndarray:
    """The separated background, lower where people talk, with the people's own voices where
    they say no line; a mixture that could not be separated is already kept quietly under the new
    voices (separate.py) and stays so."""
    if not stems.separated:
        return stems.background
    said = talking(lines, stems.background.shape[0])
    under = (1.0 - (1.0 - DUCK) * said) * stems.background.T + (1.0 - said) * stems.voices.T
    found: np.ndarray = under.T
    return found
