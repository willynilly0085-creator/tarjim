import bisect
from difflib import SequenceMatcher

from tarjim.asr.align import longest, overlapping
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

SLACK = 0.3
SEARCH = 2.0
INF = float("inf")

Limits = tuple[float, float]


def split_by(words: list[Word], utterances: list[Utterance]) -> list[list[Word]]:
    groups, cursor = [], 0
    for utterance in utterances:
        size = len(split_words(utterance.text))
        groups.append(words[cursor:cursor + size])
        cursor += size
    return groups


def inside(start: float, utterance: Utterance) -> bool:
    return utterance.start - SLACK <= start <= utterance.end + SLACK


def matched(group: list[Word], nearby: list[Word]) -> dict[int, Word]:
    matcher = SequenceMatcher(
        None, [norm(w.text) for w in group], [norm(w.text) for w in nearby], autojunk=False)
    blocks = matcher.get_matching_blocks()
    return {a + k: nearby[b + k] for a, b, size in blocks for k in range(size)}


def retime(group: list[Word], utterance: Utterance, heard: list[Word]) -> list[Word] | None:
    nearby = [w for w in heard
              if utterance.start - SEARCH <= w.start <= utterance.end + SEARCH]
    pairs = matched(group, nearby)
    if 2 * len(pairs) < len(group) or not inside(pairs[min(pairs)].start, utterance):
        return None
    times = [(pairs[i].start, pairs[i].end) if i in pairs else None for i in range(len(group))]
    return [Word(w.text, *span, w.speaker) for w, span in zip(group, fill(times), strict=True)]


def fill(times: list[tuple[float, float] | None]) -> list[tuple[float, float]]:
    known = [t for t in times if t is not None]
    result, previous_end = [], known[0][0]
    for index, known_span in enumerate(times):
        later = next((t[0] for t in times[index + 1:] if t is not None), previous_end)
        span = known_span or (previous_end, max(previous_end, later))
        result.append(span)
        previous_end = span[1]
    return result


def fits(group: list[Word], floor: float, ceiling: float) -> bool:
    return floor <= group[0].start and group[-1].end <= ceiling


def capped(group: list[Word]) -> list[Word]:
    return [Word(w.text, max(w.start, w.end - longest(w.text)), w.end, w.speaker) for w in group]


def room(index: int, groups: list[list[Word]], over: list[bool], floor: float) -> Limits:
    """Where a retimed utterance may go: between the turns around it, or anywhere near its own
    time when it was said over another turn."""
    if over[index]:
        return 0.0, INF
    later = (g[0].start for g, said_over in zip(groups[index + 1:], over[index + 1:], strict=True)
             if g and not said_over)
    return floor, next(later, INF)


def retimed(group: list[Word], utterance: Utterance, heard: list[Word],
            limits: Limits) -> list[Word]:
    better = retime(group, utterance, heard)
    return capped(better) if better and fits(better, *limits) else group


def fuse(words: list[Word], utterances: list[Utterance], heard: list[Word]) -> list[Word]:
    groups = split_by(words, utterances)
    over = overlapping(utterances)
    result: list[list[Word]] = []
    said_over: list[list[Word]] = []
    floor = 0.0
    for index, (group, utterance) in enumerate(zip(groups, utterances, strict=True)):
        if group and not inside(group[0].start, utterance):
            group = retimed(group, utterance, heard, room(index, groups, over, floor))  # noqa: PLW2901
        (said_over if over[index] else result).append(group)
        if group and not over[index]:
            floor = group[-1].end
    return slotted([w for group in result for w in group], said_over)


def slotted(turns: list[Word], replies: list[list[Word]]) -> list[Word]:
    """A short reply said over a turn goes inside it, at its own time, as one piece. Only these
    move: sorting every word by time would interleave two people talking at once, word by word,
    into a line per word (seen on 2026-10-29 when a question and its answer overlapped)."""
    words = list(turns)
    for reply in (r for r in replies if r):
        at = bisect.bisect_right([w.start for w in words], reply[0].start)
        words[at:at] = reply
    return words
