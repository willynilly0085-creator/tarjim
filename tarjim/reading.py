"""How long a subtitle's words take to read (2026-11-09).

The shortest a subtitle is shown (rules.shortest) says nothing of how much it holds: two voices
crossing put eight words in 1.36 s on en_debate_overlap, and a subtitle cut where the other voice
began held "A ban is the only rule that" for 0.94 s. Words are counted as asr/sanity counts them
(a character of a script written without spaces is a quarter of one), and read at READ a second,
a little under the fastest anyone talks (about 6 words a second, asr/sanity.py).
"""
from collections.abc import Iterable

from tarjim.asr.sanity import counted
from tarjim.models import Word

READ = 5.0  # words a second


def read_time(words: Iterable[Word]) -> float:
    return counted(word.text for word in words) / READ
