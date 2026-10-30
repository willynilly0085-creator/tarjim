"""A translation that slid down the slots: each slot holding the previous slot's words.

On 2026-10-30 a Gemini answer for a 2.5-minute statement put only half of slot 1 in slot 1 and
carried the rest to slot 2, and every slot after that held the one before it, so each subtitle
showed what had just been said. Long sources make long translations, so in a good answer the
lengths go together slot by slot (measured: correlation 0.82 and 0.85 on two good answers); in
that one they did not (0.0) and went together one slot later (0.55) instead.
"""
from statistics import StatisticsError, correlation

from tarjim.models import Cue

FEWEST = 8  # fewer slots say nothing reliable
MATCHED_BELOW = 0.3
LATER_BY = 0.25
# A stretch of 12 lines: measured over 14 good answers on this computer, the worst stretch still
# fitted its own lines at 0.52 and fitted the next ones 0.27 worse; the slid answer's stretches
# fitted their own at 0.40 or less and the next ones 0.17 to 1.4 better.
WINDOW = 12
WINDOW_MATCHED_BELOW = 0.45
WINDOW_LATER_BY = 0.15


def agreement(sources: list[int], texts: list[int]) -> float:
    try:
        return correlation(sources, texts)
    except StatisticsError:  # all of one length
        return 0.0


def fit(cues: list[Cue]) -> float:
    """How well each translation's length follows its own source's."""
    spoken = [c for c in cues if c.text.strip()]
    return agreement([len(c.source) for c in spoken], [len(c.text) for c in spoken])


def slid_run(sources: list[int], texts: list[int], below: float, by: float) -> bool:
    same, later = agreement(sources, texts), agreement(sources[:-1], texts[1:])
    return same < below and later > same + by


def slid(cues: list[Cue]) -> bool:
    """The whole answer, or any stretch of WINDOW lines in it: a slide can start mid-way."""
    spoken = [c for c in cues if c.text.strip()]
    if len(spoken) < FEWEST:
        return False
    sources, texts = [len(c.source) for c in spoken], [len(c.text) for c in spoken]
    starts = range(0, max(1, len(spoken) - WINDOW + 1), WINDOW // 2)
    return slid_run(sources, texts, MATCHED_BELOW, LATER_BY) or any(
        slid_run(sources[k:k + WINDOW], texts[k:k + WINDOW], WINDOW_MATCHED_BELOW,
                 WINDOW_LATER_BY) for k in starts)
