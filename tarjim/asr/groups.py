"""How the heard lines are searched for in the sound: in groups of lines close together, each
line's letters within a margin of its own time, a word kept where most of its letters are, and a
group that cannot be followed whole cut at its longest silence (asr/align.py)."""
from itertools import pairwise

import numpy as np

from tarjim.asr.ctc import FRAME, Span
from tarjim.listen.gemini_listen import Utterance
from tarjim.scripts import split_words

CHUNK_SECONDS = 240.0
WINDOW_MARGIN = 1.0


def chunks(utterances: list[Utterance]) -> list[list[Utterance]]:
    groups: list[list[Utterance]] = []
    for utterance in utterances:
        if groups and utterance.end - groups[-1][0].start <= CHUNK_SECONDS:
            groups[-1].append(utterance)
        else:
            groups.append([utterance])
    return groups


def windows(utterances: list[Utterance], low: int) -> tuple[np.ndarray, np.ndarray]:
    starts = np.array([(u.start - WINDOW_MARGIN) / FRAME - low for u in utterances])
    ends = np.array([(u.end + WINDOW_MARGIN) / FRAME - low for u in utterances])
    return starts.astype(np.int64), ends.astype(np.int64)


def densest(spans: list[Span], speech: np.ndarray) -> tuple[float, float]:
    groups = [[spans[0]]]
    for previous, current in pairwise(spans):
        between = speech[int(previous[1] / FRAME):int(current[0] / FRAME)]
        if not between.all():
            groups.append([])
        groups[-1].append(current)
    best = max(groups, key=len)
    return best[0][0], best[-1][1]


def quietest(group: list[Utterance], speech: np.ndarray) -> int:
    """Where a group is cut: before the line with the most silence between it and the lines
    before it, the widest pause breaking a tie."""
    def silence(index: int) -> tuple[int, float]:
        reach = max(u.end for u in group[:index])
        between = speech[int(reach / FRAME):max(0, int(group[index].start / FRAME))]
        return int(np.count_nonzero(~between)), group[index].start - reach

    return max(range(1, len(group)), key=silence)


def tell_evened(lines: list[Utterance], offset: float) -> None:
    """Words spread evenly over their line are not timed by the sound: said once, in the log."""
    if lines:
        count = sum(len(split_words(u.text)) for u in lines)
        print(f"aligner: {count} words in {len(lines)} lines at {offset + lines[0].start:.1f}-"
              f"{offset + max(u.end for u in lines):.1f} s could not be followed in the sound; "
              "spread evenly over their lines", flush=True)
