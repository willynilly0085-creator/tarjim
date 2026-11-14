"""What was said against what tarjim wrote, word by word.

Both are cut into the same units (tarjim's own: scripts.split_words, so Chinese and Japanese are
compared a character at a time) and written one plain way: case, punctuation and hyphens aside,
Arabic-script marks and letter shapes that people write either way made one. Then the fewest
changes that turn one into the other (the usual word error count), each unit of tarjim's told
which unit of the truth it stands for.
"""
import re
import unicodedata
from typing import NamedTuple

from tarjim.asr.numbers import said
from tarjim.listen.vote import norm
from tarjim.scripts import split_words

MARKS = re.compile("[ً-ْٰـ]")  # Arabic short vowels and the stretch mark
SHAPES = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ی": "ي", "ک": "ك",
                        "ة": "ه", "ؤ": "و", "ئ": "ي", "’": "'", "‘": "'"})
OK, SUB, INS, DEL = "ok", "sub", "ins", "del"
# written with spaces that people and listeners place differently: compared a letter at a
# time, as the unspaced scripts are (2026-11-14: Korean scored 11% wrong on spacing alone)
LETTER_BY_LETTER = ("ko",)


class Step(NamedTuple):
    kind: str  # OK, SUB (another unit in its place), INS (not said), DEL (said, not written)
    said: int | None  # index in the truth
    wrote: int | None  # index in what tarjim wrote


def plain(text: str, language: str = "") -> list[str]:
    """The text as comparable units; with a language, a number in digits as its words, so
    "1755" and the words a listener wrote for it are one thing (asr/numbers.py)."""
    text = unicodedata.normalize("NFKC", text).translate(SHAPES)
    text = MARKS.sub("", text)
    for mark in "-‑—/":
        text = text.replace(mark, " ")
    words = split_words(text)
    if language in LETTER_BY_LETTER:
        words = [letter for word in words for letter in word]
    spoken = " ".join(said(words, language)) if language else " ".join(words)
    return [unit for word in split_words(spoken.replace("-", " ")) if (unit := norm(word))]


def costs(said: list[str], wrote: list[str]) -> list[list[int]]:
    table = [[0] * (len(wrote) + 1) for _ in range(len(said) + 1)]
    for i in range(1, len(said) + 1):
        table[i][0] = i
    for j in range(1, len(wrote) + 1):
        table[0][j] = j
    for i, unit in enumerate(said, start=1):
        row, above = table[i], table[i - 1]
        for j, other in enumerate(wrote, start=1):
            row[j] = min(above[j - 1] + (unit != other), above[j] + 1, row[j - 1] + 1)
    return table


def step_back(table: list[list[int]], i: int, j: int, same: bool) -> tuple[str, int, int]:
    here = table[i][j]
    if i and j and here == table[i - 1][j - 1] + (not same):
        return (OK if same else SUB), i - 1, j - 1
    if i and here == table[i - 1][j] + 1:
        return DEL, i - 1, j
    return INS, i, j - 1


def steps(said: list[str], wrote: list[str]) -> list[Step]:
    """The fewest changes from what was said to what was written, in order."""
    table, i, j, found = costs(said, wrote), len(said), len(wrote), []
    while i or j:
        same = bool(i and j) and said[i - 1] == wrote[j - 1]
        kind, i_next, j_next = step_back(table, i, j, same)
        found.append(Step(kind, i_next if i_next < i else None, j_next if j_next < j else None))
        i, j = i_next, j_next
    return found[::-1]
