"""A colour for each speaker, so the viewer can tell who is talking.

Subtitlers have long given each extra speaker a colour of their own (white, yellow, cyan, green);
tarjim does the same, softened so they sit calmly on the picture. The speaker who talks most keeps
the usual off-white, so a video with one speaker looks as it always did. A listener names speakers
per piece of a long video ("c0.S1", "c1.S1"), and the same name in two pieces may be two people:
speakers are ranked by how much they talk within each piece, which keeps the main voice white
across pieces in an interview or a talk.
"""
import re
from collections import Counter

from tarjim.models import Cue, Word

# ASS colours are blue, green, red. Off-white F7F5F0, then yellow FFE066, cyan 8FE3F5, green A8E6A1.
MAIN = "&H00F0F5F7"
OTHERS = ("&H66E0FF&", "&HF5E38F&", "&HA1E6A8&")
PASS_TAG = re.compile(r"(?:^|(?<=\.))p\d+\.")  # the voting pass that found a line, not a speaker

Voices = dict[str, str]


def who(word: Word) -> str:
    return PASS_TAG.sub("", word.speaker)


def voices(cues: list[Cue]) -> Voices:
    talk = Counter(who(w) for cue in cues for w in cue.words if w.speaker)
    pieces: dict[str, list[str]] = {}
    for name, _ in talk.most_common():
        pieces.setdefault(name.rpartition(".")[0], []).append(name)
    return {name: OTHERS[(rank - 1) % len(OTHERS)]
            for names in pieces.values() for rank, name in enumerate(names) if rank}


def line_voices(cue: Cue, count: int, known: Voices) -> list[str]:
    """The colour tag of each shown line: a dialogue line is its speaker's, else the cue's."""
    speakers = [who(part[0]) for part in cue.parts if part] or [who(w) for w in cue.words[:1]]
    if len(speakers) != count:
        speakers = (speakers[:1] or [""]) * count
    return [f"{{\\c{known[s]}}}" if s in known else "" for s in speakers]
