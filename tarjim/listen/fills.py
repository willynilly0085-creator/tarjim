"""The fills kept with a hearing, judged again against the lines chosen now.

A fill was made for a stretch the lines chosen on that run left out. A later run may choose other
lines (the vote fixed, the local listener installed, a pass the sanity check no longer drops), and
those may say the same speech. Until 2026-11-08 every kept fill was added to them unchecked, so
the sentence was shown and translated twice. Now a fill stays only while the stretch it filled is
still left out and its words are not said by the lines chosen, with the checks the fills were made
with (listen/repair.py, listen/novel.py). A fill with no stretch (from the words' check after
alignment, or kept before 2026-11-08) is judged by its words alone, since the stretch a timed word
leaves out cannot be told before the timing.
"""
from tarjim.listen.coverage import EDGE, gap_seconds, merged, outside
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Fill, Span
from tarjim.listen.novel import said_before
from tarjim.listen.repair import overlaps, repeats


def still_open(gap: Span, lines: list[Utterance]) -> bool:
    """As much of the stretch as makes a gap is still outside every line. Told from the lines
    alone, so it holds with no voice detector and no local listener."""
    covered = merged([(u.start - EDGE, u.end + EDGE) for u in lines], 0.0)
    free = sum(end - start for start, end in outside(gap, covered))
    return free >= min(gap_seconds(), gap[1] - gap[0])


def needed(fill: Fill, lines: list[Utterance]) -> bool:
    if fill.gap is None:
        return not said_before(fill.line, lines)
    return (still_open(fill.gap, lines) and not overlaps(fill.line, lines)
            and not repeats(fill.line, lines))


def still_needed(fills: list[Fill], lines: list[Utterance]) -> list[Fill]:
    kept = [fill for fill in fills if needed(fill, lines)]
    if len(kept) < len(fills):
        print(f"coverage: {len(fills) - len(kept)} kept fill line(s) are said by the lines chosen "
              "now; left out", flush=True)
    return kept
