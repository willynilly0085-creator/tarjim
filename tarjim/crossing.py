"""The first words of a long turn said over the end of another, as a reply (2026-11-09).

Such a reply shares the screen with the other voice's last words (dialogue.handed_over), and
the turn's next words come up right after it, so that subtitle is shown about as long as the
two voices are heard at once; the other voice's words before it keep a subtitle of their own,
shown only until the reply is said. Since the aligner times the crossing where it is said
(asr/waited.py) that left four subtitles on every en_debate_overlap run shown faster than they
can be read: "A ban is the only rule that" 0.94 s, "actually works. / You keep saying" 0.90 s.
The reply is now taken unless one of them would be shown faster than reading.READ words a
second, and faster than the other voice's subtitle would be without the reply (shown until its
words end), the shared one given up to fit.LATE_START past the turn's next word. Without it
the turn stays whole and its subtitle waits for the other one to be read (fit.read_in_time).
"""
from itertools import pairwise

from tarjim.asr.sanity import counted
from tarjim.dialogue import fits_one_line
from tarjim.fit import LATE_START
from tarjim.models import Word, join_words
from tarjim.reading import READ
from tarjim.rules import Rules
from tarjim.speakers import who

EDGE = 0.05


def head_said_over(run: list[Word], host: list[Word], reach: float, rules: Rules) -> int:
    """How many of the run's first words are a reply: those begun before the host's words end
    (reach), when they fit one line and no subtitle around them is left too fast to be read
    and faster than the host's own would be without the reply; else none."""
    over = sum(1 for word in run if word.start < reach - EDGE)
    if over >= len(run) or not fits_one_line(run[:over], rules):
        return 0
    start, turn = run[0].start, last_turn(host)
    before = shown_before([w for w in turn if w.end <= start + EDGE], rules)
    during = [word for word in turn if word.end > start + EDGE]
    alone = pace(shown_before(turn, rules), reach)
    opens = min(start, *(word.start for word in during))
    shared = pace([*during, *run[:over]], run[over].start + LATE_START, opens)
    if said_once(before) and rushed(pace(before, start), alone):
        return 0
    return 0 if rushed(shared, alone) else over


def pace(words: list[Word], until: float, since: float | None = None) -> float:
    """Words a second shown from since (the first word's start) until then."""
    span = until - (words[0].start if since is None else since)
    return counted(word.text for word in words) / span if span > 0 else float("inf")


def rushed(shown: float, alone: float) -> bool:
    return shown > READ and shown > alone


def said_once(words: list[Word]) -> bool:
    """Words one voice says one after another. A voice heard twice at once (a line the listener
    gave twice, or slipped over another) is not read faster in either order: its reply is taken
    as before 2026-11-09 (en_long_three_pieces and en_long_seven with such faults)."""
    return bool(words) and all(b.start >= a.end - EDGE for a, b in pairwise(words))


def last_turn(host: list[Word]) -> list[Word]:
    first = len(host) - 1
    while first and who(host[first - 1].speaker) == who(host[-1].speaker):
        first -= 1
    return host[first:]


def shown_before(words: list[Word], rules: Rules) -> list[Word]:
    """The last of the words one subtitle can hold: the words before the reply are shown with
    as many of the same voice's words before them as fit (dialogue.merge_short, fit.joined)."""
    first = 0
    while first + 1 < len(words) and len(join_words(words[first:])) > rules.max_source_chars:
        first += 1
    return words[first:]
