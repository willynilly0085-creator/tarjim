"""Where a run of words is best cut in two: after a sentence's end, then after a clause's, at
the widest pause, near the middle. Moved here from segment.py on 2026-11-08 so the cue solver
cuts a turn the way a long block is cut (crowded.handed)."""
from collections.abc import Sequence

from tarjim.models import Word

SENTENCE_END = (".", "?", "!", "؟", "。", "？", "！")
SOFT_END = (",", "،", ";", "؛", ":", "，", "、", "；", "：")
SPAN_FLOOR = 1e-6  # keeps a block of zero-length words from dividing by zero


def best_split(block: list[Word], allowed: Sequence[int] | None = None) -> int:
    """The index the block is cut before, among `allowed` (every gap when None)."""
    middle = (block[0].start + block[-1].end) / 2
    span = max(block[-1].end - block[0].start, SPAN_FLOOR)

    def score(index: int) -> float:
        prev, word = block[index - 1], block[index]
        text = prev.text.rstrip()
        bonus = 2.0 if text.endswith(SENTENCE_END) else 1.0 if text.endswith(SOFT_END) else 0.0
        off_center = abs((prev.end + word.start) / 2 - middle) / span
        return bonus + 2 * (word.start - prev.end) - off_center

    return max(range(1, len(block)) if allowed is None else allowed, key=score)
