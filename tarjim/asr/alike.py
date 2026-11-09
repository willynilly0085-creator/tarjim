"""Of one speaker's lines written alike, which the tolerant aligner keeps (asr/unplaced.settled,
2026-11-09).

The skip reads a copy's speaker's lines in order and may place any of the lines written alike on
the speech said once: on en_refrain_close x loop_all it placed the last copy and left out the
line itself, so the words had the right times but came after the next speaker's line in the
transcript, out of order. Of such lines the first written are kept, each with the times the
reading found for the ones it placed, in order; the rest are the copies dropped.
"""
from dataclasses import replace

from tarjim.asr.unplaced import NEAR
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words


def alike(lines: list[Utterance], line: int, later: int) -> bool:
    """The later line the same speaker's same words, within NEAR seconds."""
    u, v = lines[line], lines[later]
    said = [[norm(t) for t in split_words(x.text)] for x in (u, v)]
    return u.speaker == v.speaker and said[0] == said[1] and v.start <= u.end + NEAR


def first_written(words: list[Word], dropped: set[int], lines: list[Utterance],
                  owner: list[int]) -> set[int]:
    """The words dropped once each dropped line written alike with a later line kept takes
    that line's times, and the later line goes instead; `words` take the times."""
    first: dict[int, int] = {}
    for index, k in enumerate(owner):
        first.setdefault(k, index)
    gone = {owner[i] for i in dropped}
    for line in range(len(lines)):
        later = next((k for k in range(line + 1, len(lines)) if k not in gone
                      and alike(lines, line, k)), None) if line in gone else None
        if later is None:
            continue
        mine, theirs = first[line], first[later]
        found = words[theirs:theirs + len(split_words(lines[later].text))]
        words[mine:mine + len(found)] = [
            replace(words[mine + n], start=w.start, end=w.end, score=w.score, source=w.source)
            for n, w in enumerate(found)]
        gone = (gone - {line}) | {later}
    return {i for i, k in enumerate(owner) if k in gone}
