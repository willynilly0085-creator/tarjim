"""Short lines go where their label went.

A line too short to know a voice by is never judged by its own print (listen/whose.py): a short
reply's print is mostly noise. But when the listener swapped two speakers from some point on, the
long lines of a label are put right, and a short line with the same label was left in the middle
of them wearing the other speaker's colour. Since 2026-11-08 a short line takes the speaker that
its label's nearest long lines were given, on both sides of it (or on the one side there is, at
the start or end of the clip). Where they did not all move the same way it keeps its label. It
never simply takes the turn it touches: a short reply is most often the other person's, and the
listener heard whose it was.
"""
from bisect import bisect

from tarjim.models import Word
from tarjim.speakers import Line, lines, who

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
