"""Who is speaking, from the listener's labels. A label may carry the voting pass that found a line
("p2.S1", tarjim/listen/vote.py): that names the pass, not another person. A long video is heard
in pieces, each naming its own speakers ("c0.S1", "c1.S1"), and the same name in two pieces may be
two people: speakers are ranked by how much they talk within their piece, so the main voice of
every piece shares one rank."""
import re
from collections import Counter
from collections.abc import Iterable

from tarjim.models import Word

PASS_TAG = re.compile(r"(?:^|(?<=\.))p\d+\.")


def who(label: str) -> str:
    return PASS_TAG.sub("", label)


def ranked(words: Iterable[Word]) -> dict[str, int]:
    """Each speaker's place by talk within their piece: 0 for the one who talks most."""
    talk = Counter(who(w.speaker) for w in words if w.speaker)
    taken: Counter[str] = Counter()
    ranks: dict[str, int] = {}
    for name, _ in talk.most_common():
        piece = name.rpartition(".")[0]
        ranks[name], taken[piece] = taken[piece], taken[piece] + 1
    return ranks
