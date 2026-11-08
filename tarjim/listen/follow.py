"""Short lines go where their label went.

A line too short to know a voice by is never judged by its own print (listen/whose.py): a short
reply's print is mostly noise. But when the listener swapped two speakers from some point on, the
long lines of a label are put right, and a short line with the same label was left in the middle
of them wearing the other speaker's colour. Since 2026-11-08 a short line takes the speaker that
its label's nearest long lines were given, on both sides of it (or on the one side there is, at
the start or end of the clip). Where they did not all move the same way it keeps its label. It
never simply takes the turn it touches: a short reply is most often the other person's, and the
listener heard whose it was.

A speaker another listening pass heard but the vote could not link to the base pass's ("S2~p3",
listen/vote.relabel) is one of the base's speakers too. Since 2026-11-08 its lines go, together,
to the base speaker whose average voice is nearest to theirs: judged alone, a label with one line
had no average to leave it out of, so it was never moved and stayed a third speaker.
"""
from bisect import bisect

import numpy as np

from tarjim.models import Word
from tarjim.speakers import Line, lines, unlinked, who

Labels = dict[Line, str]


def around(line: Line, same: list[Line]) -> list[Line]:
    """The nearest of the sorted lines before a line, and the nearest after it."""
    at = bisect(same, line)
    return same[max(at - 1, 0):at] + same[at:at + 1]


def followed(words: list[Word], heard: Labels, labels: Labels) -> Labels:
    """Each short line whose label's long lines on either side were all given to one other
    speaker, with that speaker; heard are the long lines' labels as heard, labels as judged."""
    by_label = {name: sorted(k for k in heard if heard[k] == name) for name in set(heard.values())}
    found: Labels = {}
    for line in lines(words):
        own = who(words[line[0]].speaker)
        names = {labels[k] for k in around(line, by_label.get(own, []))}
        if line not in heard and len(names) == 1 and own not in names:
            found[line] = names.pop()
    return found


def adopted(voices: dict[str, np.ndarray]) -> dict[str, str]:
    """Each unlinked label among the speakers' average voices as the base speaker whose voice is
    nearest to its own; none when the clip has no base speaker's voice to go by."""
    base = {name: voice / np.linalg.norm(voice) for name, voice in voices.items()
            if not unlinked(name) and np.linalg.norm(voice) > 0}
    if not base:
        return {}
    return {name: max(base, key=lambda known: float(base[known] @ voice))
            for name, voice in voices.items() if unlinked(name)}
