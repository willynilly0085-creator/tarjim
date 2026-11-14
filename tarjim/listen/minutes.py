"""Times a listener wrote as minutes and seconds with the colon left out: 1:09 as 109.

A cloud listener asked for seconds sometimes answers in the clock's own form from the first
minute on and writes it as one number: 1:09.12 comes back as 109.12, forty seconds late. On
2026-11-14 two of three passes over a 96-second clip did. The line said over the minute kept its
start and ran to the clip's end, every line after it was put at the clip's edge with no time, the
two passes outvoted the one that was right (the first piece's passes were voted as written), and
the last third of the clip was never shown: a few misheard words stood in its place.

No time between 60 and 100 s can be written so (its seconds would be 60 or more). So a pass whose
every time from the first minute on is 100 or more, and reads back inside its request, is written
so throughout: it is read back whole, before the passes are voted. In a request longer than 100 s
such a pass may also be right as it stands. The line said over the minute then decides, by which
reading is nearer the time its letters take to say; with no such line, the request's other
passes do: one that timed a line between 60 and 100 s heard speech where this pass has none as
it stands, and with no such pass it is left as heard. One line written so among lines in
seconds is read back on its own, as since 2026-11-08.
"""
from dataclasses import replace

from tarjim import guards
from tarjim.listen.gemini_listen import SECONDS_PER_LETTER, SHORTEST, Utterance

MINUTE = 60.0  # seconds
WRITTEN = 100.0  # the first minute as it is written without its colon
OVERRUN = 1.0  # seconds past its request's end a line may be heard to run
SLIPPED = 0.5  # how far the time of a line read back from such a writing is trusted

Span = tuple[float, float]
Run = list[Utterance]


def undone(seconds: float) -> float | None:
    """A time read as minutes and seconds written without the colon (1:05 as 105), or None when
    it cannot be one."""
    minutes, rest = divmod(seconds, WRITTEN)
    return MINUTE * minutes + rest if rest < MINUTE else None


def back(seconds: float) -> float:
    """The time read back; one under a minute is written the same either way."""
    found = undone(seconds) if seconds >= WRITTEN else None
    return seconds if found is None else found


def written_so(run: Run, length: float) -> bool:
    """Every time of the pass from the first minute on can only be minutes and seconds."""
    late = [t for u in run for t in (u.start, u.end) if t >= MINUTE]
    return bool(late) and all(
        t >= WRITTEN and undone(t) is not None and back(t) <= length + OVERRUN for t in late)


def nearer_read_back(u: Utterance) -> bool:
    """A line said over the minute: whether its end read back is nearer the time its letters
    take to say than its end as it stands (the two compared as ratios)."""
    told = SECONDS_PER_LETTER * len(u.text)
    return told * told < max(back(u.end) - u.start, SHORTEST) * (u.end - u.start)


def heard_between(peers: list[Run]) -> bool:
    """Another pass timed a line between 60 and 100 s: there is speech there."""
    return any(MINUTE <= t < WRITTEN for run in peers for u in run for t in (u.start, u.end))


def meant(run: Run, length: float, peers: list[Run]) -> bool:
    """A pass written so is read back when a time of it falls past its request, where nothing
    was heard; else when every line said over the minute is nearer its words read back; with
    no such line, when another pass heard speech between 60 and 100 s (heard_between), and
    otherwise not: 40 s with nothing said can be the truth (2026-11-14, found in review: it was
    read back, and a pass that was right lost 40 s)."""
    if max(u.end for u in run) > length + OVERRUN:
        return True
    over = [u for u in run if u.start < MINUTE and u.end >= WRITTEN]
    return all(nearer_read_back(u) for u in over) if over else heard_between(peers)


def line_back(u: Utterance) -> Utterance:
    start = back(u.start)
    moved = guards.when("shift.slipped", start != u.start)
    return replace(u, start=start, end=max(start, back(u.end)),
                   prior=min(u.prior, SLIPPED) if moved else u.prior)


def read_back(run: Run, length: float, peers: list[Run] | None = None) -> Run:
    """The pass at the times its listener meant, when it wrote them all as minutes and seconds;
    else the pass as it is. `peers`: the request's other passes, when they are at hand."""
    if not written_so(run, length):
        return run
    if not guards.when("shift.minutes", meant(run, length, peers or [])):
        return run
    return [line_back(u) for u in run]


def read_back_all(runs: list[Run], length: float) -> list[Run]:
    """Every pass of one request, each judged beside the others."""
    return [read_back(run, length, [other for other in runs if other is not run])
            for run in runs]


def ended(u: Utterance, high: float) -> float:
    """Where a line begun inside its request ends: its end read back when that is written as
    minutes and seconds and falls inside the request after the line's start, else no later than
    the request's end. Until 2026-11-14 it always ran to the request's end, and no line after
    it could be read back: each landed on it."""
    if u.end <= high:
        return max(u.start, u.end)
    found = undone(u.end)
    return found if found is not None and u.start <= found <= high else max(u.start, high)


def unslipped(u: Utterance, length: float, room: Span) -> Utterance | None:
    """The line at the time its writing as minutes and seconds reads back to, when that falls
    inside the piece between the end of the line before it and the start of the line after it:
    one that lands on another line was not written so (2026-11-08: only the line before was
    checked, and a line said at 45 s read back to 65 s, among the lines after it)."""
    start, end = undone(u.start), undone(u.end)
    if start is None or not room[0] <= start <= length:
        return None
    end = end if end is not None and end >= start else start + u.end - u.start
    end = max(start, min(end, length + OVERRUN))
    return replace(u, start=start, end=end, prior=SLIPPED) if end <= room[1] else None


def room(placed: Run, rest: Run, length: float) -> Span:
    """Where a line written so may be read back to: after the line placed before it and before
    the next line of the piece in the listener's order (a raw pass is not sorted, 2026-11-08).
    A line before it that was cut at the request's end says only where it began."""
    high = length + OVERRUN
    later = next((u.start for u in rest if u.start < high), high)
    if not placed:
        return 0.0, later
    last = placed[-1]
    return (last.start if last.end >= high else last.end), later
