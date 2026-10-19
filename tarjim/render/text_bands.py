"""Where the picture already carries text: captions the creator burned in, a channel name, a news
ticker. No reading, only the look of it: text drawn on video is light strokes with dark edges
packed into a level stripe a line high, and it stays where it is while the picture moves.

In each frame a row counts when many of its neighbouring pixels differ sharply on a light side;
rows like that which form a stripe of text height are kept (a taller patch is part of the
picture: foliage, a striped wall); a stripe kept in a good share of the frames is a text band.
Rows outside the subtitle's side margins are not looked at: text there never meets it."""
import numpy as np

from tarjim.render.frames import Frame

STEP = 48
LIGHT = 150
DENSE = 0.05
SIDE = 0.06
SHORTEST = 0.012
TALLEST = 0.12
JOIN = 2
# The dense rows are the body of the letters; capitals, ascenders and descenders reach past them
# by about this share of the body's height.
REACH = 0.4
SHARE = 0.3
FEWEST = 4
Band = tuple[float, float]


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Each stretch of True as (first, past the last)."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return [(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def text_rows(frame: Frame) -> np.ndarray:
    pixels = frame.astype(np.int16)
    side = round(pixels.shape[1] * SIDE)
    left, right = pixels[:, side:-side - 1], pixels[:, side + 1:-side]
    sharp = (np.abs(left - right) >= STEP) & (np.maximum(left, right) >= LIGHT)
    return np.asarray(sharp.mean(axis=1) >= DENSE)


def stripes(frame: Frame) -> np.ndarray:
    rows = text_rows(frame)
    height = len(rows)
    for start, end in runs(~rows):
        if start > 0 and end < height and end - start <= JOIN:
            rows[start:end] = True
    kept = np.zeros(height, bool)
    for start, end in runs(rows):
        if SHORTEST * height <= end - start <= TALLEST * height:
            kept[start:end] = True
    return kept


def text_bands(frames: list[Frame]) -> list[Band]:
    """Each band as (top, bottom), in parts of the picture's height from its top."""
    if len(frames) < FEWEST:
        raise ValueError(f"only {len(frames)} frames could be read")
    share = np.mean([stripes(frame) for frame in frames], axis=0)
    height = len(share)
    return [(max(0.0, (start - REACH * (end - start)) / height),
             min(1.0, (end + REACH * (end - start)) / height))
            for start, end in runs(share >= SHARE)]
