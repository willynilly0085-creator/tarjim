"""How often each layer that makes up for another layer's mistake fired in the running job.

Many steps exist only to correct an earlier one: the anchor moves a cloud listener's drifted
lines, fuse re-times words the aligner put outside their line, the piles check spreads words the
aligner squeezed onto one instant, and so on. Since 2026-11-08 each of them counts its fires here,
so the bench can tell which still matter before any is retired. Nothing reads the counts to
decide anything: the job does exactly what it did without them. They start again with every job
(findings.collecting) and every bench cell (reset), are written to the log once per job in one
line, and are kept on the job's findings.
"""
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

# Every guard, so each shows in the counts with 0 when it never fired.
NAMES = (
    "opinion.no_length",  # local words with no length one says them in, left out (2026-11-08)
    "opinion.not_found",  # ...not heard where they are timed
    "opinion.stretch",  # ...in a stretch whose local words were mostly not heard where timed
    "opinion.unused",  # ...all of them: hardly any was heard where timed
    "anchor.moved",  # a line moved to where the local listener heard its words
    "fuse.retimed",  # a line's words re-timed by the local listener's times
    "align.evened",  # lines spread evenly over their time: the sound could not follow them
    "align.said_over",  # short replies said over a turn, aligned on their own
    "align.unwaited",  # turns begun over another's end, timed again inside their own time
    "timing.apart",  # added lines aligned in more than one stretch of sound
    "coverage.local_only",  # speech known only from local words, outside the voice detector's
    "wordcover.unpiled",  # a pile of words by a gap re-timed
    "wordcover.realigned",  # ...by aligning it again
    "piles.spread",  # ...by spreading it over its speech
    "wordcover.fills",  # lines the words' check added
    "sanity.implausible",  # a timing no one could speak
    "settle.trusted",  # the local words used in place of an implausible timing
    "settle.second_timing",  # the lines timed again on the sound alone
    "settle.alone_won",  # ...and that timing kept
    "merge.sane_line",  # lines of a pass no one could speak, left out
    "merge.sane_pass",  # a whole pass left out for its broken lines
    "merge.fullest",  # the fullest pass kept over a vote that lost words
    "recover.not_vote",  # a pass the local words back more kept over the vote
    "recover.fuller",  # the middle pass kept over a vote that kept under half of it
    "vote.extras",  # lines the base pass missed that other passes heard
    "vote.extra_dropped",  # ...left out as a copy of a line already kept
    "repair.overlaps",  # a line heard again inside a line already there
    "repair.repeats",  # a line heard again that says what a line close by says
    "repair.fills",  # lines the lines' check added
    "novel.said_before",  # a line heard again after alignment that was said nearby
    "novel.timed_over",  # ...whose time timed words already fill
    "novel.echoes",  # ...that echoes timed words close by
    "shift.dropped",  # a line past its piece's end, dropped
    "kept.implausible",  # a kept transcript whose timing no one could speak
    "kept.rederived",  # a kept transcript made by other code, derived again
    "kept.revoted",  # a kept hearing voted again piece by piece
)

COUNTS: ContextVar[Counter[str] | None] = ContextVar("guards", default=None)
COUNTING = threading.Lock()  # a job's listening passes run in threads of their own
QUIET: ContextVar[bool] = ContextVar("guards_quiet", default=False)


def reset() -> None:
    """Counts of nothing for the job this thread runs."""
    COUNTS.set(Counter())


def current() -> Counter[str]:
    found = COUNTS.get()
    if found is None:  # no job started: the command line or a test
        reset()
        found = COUNTS.get() or Counter()
    return found


@contextmanager
def quiet() -> Iterator[None]:
    """Nothing counts inside: work done again by a later step that counts it. Each decision
    counts once, at the step whose result the job keeps (2026-11-08: one broken line counted
    three times on a fresh hearing and twice on a kept one, so the two never matched)."""
    token = QUIET.set(True)
    try:
        yield
    finally:
        QUIET.reset(token)


def fired(name: str, times: int = 1) -> None:
    """The guard `name` fired `times` times."""
    if QUIET.get():
        return
    found = current()
    with COUNTING:
        found[name] += max(times, 0)


def when(name: str, happened: bool) -> bool:
    """Whether it happened, counted when it did."""
    if happened:
        fired(name)
    return happened


def counts() -> dict[str, int]:
    """Every guard's count in the running job, those not in NAMES after them."""
    found = current()
    with COUNTING:
        others = sorted(set(found) - set(NAMES))
        return {name: found[name] for name in (*NAMES, *others)}


def said(found: dict[str, int]) -> str:
    """The counts as one line for the log: the guards that fired; all others fired 0 times."""
    shown = " ".join(f"{name}={count}" for name, count in found.items() if count)
    return f"guards: {shown or 'none fired'}"
