import bisect
from dataclasses import replace
from difflib import SequenceMatcher

from tarjim import guards
from tarjim.asr.align import Slot, fill_gaps, longest, overlapping, share
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


def retime(group: list[Word], utterance: Utterance, heard: list[Word],
           limits: Limits) -> list[Word] | None:
    nearby = [w for w in heard
              if utterance.start - SEARCH <= w.start <= utterance.end + SEARCH]
    pairs = matched(group, nearby)
    if 2 * len(pairs) < len(group) or not inside(pairs[min(pairs)].start, utterance):
        return None
    times = [(pairs[i].start, pairs[i].end) if i in pairs else None for i in range(len(group))]
    own = max(limits[0], utterance.start), min(limits[1], utterance.end)
    spans = fill([w.text for w in group], times, own)
    return [Word(w.text, *span, w.speaker, source="unplaced" if time is None else "heard")
            for w, span, time in zip(group, spans, times, strict=True)]


def fill(texts: list[str], times: list[tuple[float, float] | None],
         room: Limits) -> list[tuple[float, float]]:
    """Words the local listener did not hear share the time between the words around them, each
    by its length, as the aligner's own do (asr/align.fill_gaps). Before 2026-11-08 the second
    and later of a run all sat on one instant, zero long."""
    slots = [Slot(text, "", 0, *(span or (0.0, 0.0)), timed=span is not None)
             for text, span in zip(texts, times, strict=True)]
    fill_gaps(slots)
    kept_in(slots, room)
    return [(slot.start, slot.end) for slot in slots]


def kept_in(slots: list[Slot], room: Limits) -> None:
    """Unheard words before the first heard one or after the last share only the room the line
    has: its own time and the turns around it. A fixed length past the heard words crossed a
    close neighbour, the retime was refused and the line stayed seconds off (2026-11-08); with
    no room left they sit on the heard word's edge, as they did before."""
    heard = [index for index, slot in enumerate(slots) if slot.timed]
    first, last = heard[0], heard[-1]
    if first:
        after = slots[first].start
        share(slots[:first], min(after, max(room[0], slots[0].start)), after)
    if last < len(slots) - 1:
        before = slots[last].end
        share(slots[last + 1:], before, max(before, min(room[1], slots[-1].end)))


def fits(group: list[Word], floor: float, ceiling: float) -> bool:
    return floor <= group[0].start and group[-1].end <= ceiling


def capped(group: list[Word]) -> list[Word]:
    return [replace(w, start=max(w.start, w.end - longest(w.text))) for w in group]


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
    better = retime(group, utterance, heard, limits)
    if not (better and fits(better, *limits)):
        return group
    guards.fired("fuse.retimed")
    return capped(better)


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
