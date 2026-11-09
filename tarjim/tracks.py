"""The heard words in an order the cue builder can trust (2026-11-08).

Listeners hand words over in the order they took them, which is not always time order: the
aligner times a reply said over a turn on its own and puts it after that turn, and the word
fill slots a reply in by its start, inside the host's sentence. Here the words are put back in
time order a whole run at a time (a run is what the listener gave in order: one speaker, time
never going back), so two long turns said at once stay whole instead of alternating word by
word. A short reply said over another turn is set aside, to become a part of the subtitle that
holds its time (dialogue.with_replies), and so are the first words of a long labelled turn said
over the end of another (over_end). The repair is logged, never asserted: a job never
fails because a listener gave its words out of order.
"""
import logging
from bisect import bisect_left
from itertools import pairwise
from typing import NamedTuple

from tarjim.crossing import head_said_over
from tarjim.dialogue import fits_one_line
from tarjim.models import Word
from tarjim.rules import DEFAULT_RULES, Rules
from tarjim.speakers import who

# The same test as asr.align.overlapping, which this mirrors for words from every listener.
SHORT_REPLY = 4  # words: "Really?", "Oh my gosh", not a turn of its own
OVERLAP = 1.0  # starting this far inside an earlier turn: said over it, not after it
SAID_OVER = 0.5  # seconds a long turn of another voice starts before the last one ends
EDGE = 0.05

Run = list[Word]
Host = tuple[list[Word], float]  # the main track so far, and where its words end


class Timeline(NamedTuple):
    words: list[Word]
    starts: list[int]  # the words' places, earliest start first


log = logging.getLogger(__name__)


def tracks(words: list[Word], rules: Rules = DEFAULT_RULES) -> tuple[list[Word], list[Run]]:
    """The main track, one turn after another in time, and the replies said over it."""
    kept, slotted = unslotted(words)
    ordered = in_order(kept, rules)
    main: list[Word] = []
    replies: list[Run] = list(slotted)
    reach = float("-inf")
    for index, run in enumerate(ordered):
        following = ordered[index + 1] if index + 1 < len(ordered) else None
        over = taken(run, (main, reach), following, rules) if main else 0
        if over:
            replies.append(run[:over])
        main.extend(run[over:])
        reach = max([reach, *(word.end for word in run[over:])])
    return main, replies


def taken(run: Run, host: Host, following: Run | None, rules: Rules) -> int:
    """How many of the run's first words are said over the turn before it."""
    if said_over(run, host, following, rules):
        return len(run)
    return over_end(run, host, rules)


def over_end(run: Run, host: Host, rules: Rules) -> int:
    """A labelled turn of another voice begun well before the last one ends (2026-11-08): the
    words said while that one is still said are a reply, a part of the subtitle that holds
    their time, and the rest goes on the main track. Before, the turn's subtitle came up only
    once the other one's had gone, or cut its last words. The whole turn is the reply when it
    fits one line of an exchange; only its first words when they and the words around them
    can be read in the time they get (crossing.head_said_over, 2026-11-09)."""
    main, reach = host
    voice, replier = who(main[-1].speaker), who(run[0].speaker)
    if len(run) <= SHORT_REPLY or not (voice and replier) or voice == replier:
        return 0
    if run[0].start >= reach - SAID_OVER:
        return 0
    if fits_one_line(run, rules):
        return len(run)
    return head_said_over(run, main, reach, rules)


def in_order(words: list[Word], rules: Rules = DEFAULT_RULES) -> list[Run]:
    timeline = Timeline(words, sorted(range(len(words)), key=lambda k: words[k].start))
    given = [part for run in runs(words) for part in opened(run, timeline, rules)]
    ordered = sorted(given, key=lambda run: run[0].start)
    if ordered != given:
        log.info("heard words out of time order: %d runs put back in order", len(given))
    return ordered


def runs(words: list[Word]) -> list[Run]:
    labelled = any(word.speaker for word in words)
    found: list[Run] = []
    for word in words:
        if found and continues(found[-1][-1], word, labelled):
            found[-1].append(word)
        else:
            found.append([word])
    return found


def continues(prev: Word, word: Word, labelled: bool) -> bool:
    same = not labelled or who(prev.speaker) == who(word.speaker)
    return same and word.start >= prev.start


def opened(run: Run, timeline: Timeline, rules: Rules) -> list[Run]:
    """A run's first few words stop at a pause in which somebody else speaks, longer than any
    subtitle joins across: a reply, then the replier's own later turn, given as one run
    (2026-11-08). The reply alone can then be read as said over the turn. Two people talking
    at once leave no such pause, so their turns stay whole."""
    mine = {id(word) for word in run}
    for index in range(1, min(len(run), SHORT_REPLY + 1)):
        after, before = run[index - 1].end, run[index].start
        if before - after > rules.join_gap and spoken_between(after, before, timeline, mine):
            return [run[:index], run[index:]]
    return [run]


def spoken_between(after: float, before: float, timeline: Timeline, mine: set[int]) -> bool:
    """Whether a whole word of somebody else's lies in this pause."""
    words, starts = timeline
    first = bisect_left(starts, after - EDGE, key=lambda k: words[k].start)
    for k in starts[first:]:
        word = words[k]
        if word.start > before + EDGE:
            return False
        if word.end <= before + EDGE and id(word) not in mine:
            return True
    return False


def said_over(run: Run, host: Host, following: Run | None, rules: Rules) -> bool:
    """A short reply said inside the turn before it: starting well inside it, as the aligner
    tests, or overlapping it while that speaker goes on right after it."""
    main, reach = host
    voice, replier = who(main[-1].speaker), who(run[0].speaker)
    if len(run) > SHORT_REPLY or (replier and replier == voice):
        return False  # one person's own words stay on the main track
    if run[0].start < reach - OVERLAP:
        return True
    if following is None or not voice or who(following[0].speaker) != voice:
        return False
    if following[0].start - run[-1].end > rules.join_gap:
        return False  # the turn had ended: a quick answer to it, not words said over it
    return run[0].start < reach - EDGE or following[0].start < run[-1].end - EDGE


def unslotted(words: list[Word]) -> tuple[list[Word], list[Run]]:
    """Without speaker labels, a reply slotted in by its start (asr.fuse.slotted) shows only by
    time: it starts inside the word before it and the next word starts inside it, while the
    words around it follow each other cleanly. It is set aside like a labelled reply instead
    of being read into the host's sentence (2026-11-08)."""
    if any(word.speaker for word in words):
        return words, []
    kept: list[Word] = []
    replies: list[Run] = []
    index = 0
    while index < len(words):
        past = slotted_from(words, index)
        if past:
            replies.append(words[index:past])
        else:
            kept.append(words[index])
        index = past or index + 1
    return kept, replies


def slotted_from(words: list[Word], index: int) -> int:
    """Where a reply slotted in at index ends, or 0 when no reply starts there."""
    if index == 0 or not entered(words, index):
        return 0
    for past in range(index + 1, min(index + SHORT_REPLY, len(words) - 1) + 1):
        if words[past].start < max(w.end for w in words[index:past]) - EDGE:
            return past if around_cleanly(words, index, past) else 0
    return 0


def entered(words: list[Word], index: int) -> bool:
    before, word = words[index - 1], words[index]
    return before.start <= word.start < before.end - EDGE


def around_cleanly(words: list[Word], index: int, past: int) -> bool:
    host = [words[k] for k in (index - 2, index - 1, past, past + 1) if 0 <= k < len(words)]
    return all(first.end <= second.start + EDGE for first, second in pairwise(host))
