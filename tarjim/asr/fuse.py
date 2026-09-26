from difflib import SequenceMatcher

from tarjim.asr.align import longest
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word

SLACK = 0.3
SEARCH = 2.0
INF = float("inf")


def split_by(words: list[Word], utterances: list[Utterance]) -> list[list[Word]]:
    groups, cursor = [], 0
    for utterance in utterances:
        size = len(utterance.text.split())
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


def fuse(words: list[Word], utterances: list[Utterance], heard: list[Word]) -> list[Word]:
    groups = split_by(words, utterances)
    result: list[Word] = []
    for index, (group, utterance) in enumerate(zip(groups, utterances, strict=True)):
        if group and not inside(group[0].start, utterance):
            ceiling = next((g[0].start for g in groups[index + 1:] if g), INF)
            better = retime(group, utterance, heard)
            floor = result[-1].end if result else 0.0
            if better and fits(better, floor, ceiling):
                group = capped(better)  # noqa: PLW2901
        result.extend(group)
    return result
