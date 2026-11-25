"""What a rewritten dub line must still say (2026-11-25). The owner wants every repeat, stutter
and filler kept, and the first shortening round dropped them anyway ("إيه، أكيد. إيه." came back
"إيه، أكيد."; "أوه، واو" came back "واو"), whatever the prompt said. So a rewrite is checked here,
and one that lost any of them is not used."""
import math
import re
from collections import Counter

FILLERS = frozenset({"إيه", "ايه", "أوه", "اوه", "واو", "آه", "اه", "يعني", "تمام", "هلا",
                     "أوكيه", "اوكيه", "طيب", "امم", "ممم", "أها", "اها", "لا", "نعم", "أيوه"})
MARKS = re.compile("[ً-ْٰـ]")
WORD = re.compile(r"[^\W\d_]+")
FLOOR = 0.6


def words_of(text: str) -> list[str]:
    return WORD.findall(MARKS.sub("", text))


def needed(text: str) -> Counter[str]:
    """Each filler as often as the line says it, and any word the line says more than once."""
    counts = Counter(words_of(text))
    return Counter({word: n for word, n in counts.items() if word in FILLERS or n > 1})


def fewest(text: str) -> int:
    return max(1, math.ceil(len(words_of(text)) * FLOOR))


def keeps(old: str, new: str) -> bool:
    have = Counter(words_of(new))
    return (len(words_of(new)) >= fewest(old)
            and all(have[word] >= n for word, n in needed(old).items()))


def listed(text: str) -> str:
    """The words the rewrite is told it must keep, as they are counted."""
    return "، ".join(f"{word} ×{n}" if n > 1 else word for word, n in needed(text).items())
