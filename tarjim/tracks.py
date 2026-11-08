"""The heard words in an order the cue builder can trust (2026-11-08).

Listeners hand words over in the order they took them, which is not always time order: the
aligner times a reply said over a turn on its own and puts it after that turn, and the word
fill slots a reply in by its start, inside the host's sentence. Here the words are put back in
time order a whole run at a time (a run is what the listener gave in order: one speaker, time
never going back), so two long turns said at once stay whole instead of alternating word by
word. A short reply said over another turn is set aside, to become a part of the subtitle that
holds its time (dialogue.with_replies). The repair is logged, never asserted: a job never
fails because a listener gave its words out of order.
"""
import logging

from tarjim.models import Word
from tarjim.speakers import who

# The same test as asr.align.overlapping, which this mirrors for words from every listener.
SHORT_REPLY = 4  # words: "Really?", "Oh my gosh", not a turn of its own
OVERLAP = 1.0  # starting this far inside an earlier turn: said over it, not after it
EDGE = 0.05

Run = list[Word]
log = logging.getLogger(__name__)


def tracks(words: list[Word]) -> tuple[list[Word], list[Run]]:
    """The main track, one turn after another in time, and the replies said over it."""
    ordered = in_order(words)
    main: list[Word] = []
    replies: list[Run] = []
    reach = float("-inf")
    for index, run in enumerate(ordered):
        following = ordered[index + 1] if index + 1 < len(ordered) else None
        if main and said_over(run, main[-1], reach, following):
            replies.append(run)
        else:
            main.extend(run)
            reach = max(reach, *(word.end for word in run))
    return main, replies


def in_order(words: list[Word]) -> list[Run]:
    given = runs(words)
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


def said_over(run: Run, host: Word, reach: float, following: Run | None) -> bool:
    """A short reply said inside the turn before it: starting well inside it, as the aligner
    tests, or overlapping it while that speaker goes on right after."""
    voice, replier = who(host.speaker), who(run[0].speaker)
    if len(run) > SHORT_REPLY or (replier and replier == voice):
        return False  # one person's own words stay on the main track
    if run[0].start < reach - OVERLAP:
        return True
    if following is None or not voice or who(following[0].speaker) != voice:
        return False
    return run[0].start < reach - EDGE or following[0].start < run[-1].end - EDGE
