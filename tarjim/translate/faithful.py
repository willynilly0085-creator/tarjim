"""What can be told of a translation without asking a model (2026-11-14).

Until now a finished job knew only whether each line had a translation. Whether the translation
says what was said is a model's question (not asked yet); four things can be read off the two
texts all the same, on any computer and at no cost, and a line that fails one is listed for the
person to look at (tarjim/doubts.py):

- a number written in digits in what was said that the translation does not hold. Numbers under
  ten and round ones (100, 2,000) are left out: a translator may word them. Any script's digits
  and any grouping read the same, and a number said twice need be written once (a slip of the
  tongue is, translate/manner.py);
- a name from the person's glossary said in the line and not written the way they set it;
- a line much shorter, for the speech it carries, than the clip's other lines are: the usual
  is the clip's own, so no pair of languages needs a number of its own;
- a line shown exactly as it was said while most lines were translated. A clip subtitled in its
  own language is all such lines, and none is listed.
"""
import re
import unicodedata
from statistics import median

from tarjim.listen.vote import norm
from tarjim.models import Cue
from tarjim.scripts import split_words
from tarjim.translate.glossary import Glossary

GROUPED = re.compile(r"(?<!\d)\d{1,3}(?:[ ,.  ]\d{3})+(?!\d)")  # 4,000 · 4 000 · 4.000
DIGITS = re.compile(r"\d+")
SMALL = 2  # digits a number needs to be looked for: those under ten are often worded
ROUND = "00"  # how a number often worded ends: a hundred, two thousand
TOLD = 6  # words said before a line's length is compared with the others'
USUAL = 5  # lines that long a clip needs before it has a usual length
SHORT = 0.4  # of the clip's usual translated letters per letter said: under it, much shorter
ECHO = 3  # words a line needs before "shown as said" can be told from a name or a greeting
FEW = 0.5  # share of the lines shown as said under which they are the odd ones


def western(text: str) -> str:
    """Every script's digits as 0-9."""
    return "".join(str(unicodedata.decimal(ch)) if ch.isdecimal() else ch for ch in text)


def numbers(text: str) -> list[str]:
    """The numbers written in digits that a translation has to hold, in order."""
    joined = GROUPED.sub(lambda found: re.sub(r"\D", "", found.group()), western(text))
    return [n for n in DIGITS.findall(joined) if len(n) >= SMALL and not n.endswith(ROUND)]


def tokens(text: str) -> list[str]:
    return [token for word in split_words(text) if (token := norm(word))]


def letters(text: str) -> int:
    return sum(ch.isalnum() for ch in text)


def lost_number(cue: Cue) -> bool:
    return bool(set(numbers(cue.source)) - set(numbers(cue.text)))


def named(term: str, source: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", source, re.IGNORECASE) is not None


def misnamed(cue: Cue, glossary: Glossary) -> bool:
    text = cue.text.casefold()
    return any(named(term, cue.source) and meaning.casefold() not in text
               for term, meaning in glossary)


def as_said(cue: Cue) -> bool:
    said = tokens(cue.source)
    return len(said) >= ECHO and tokens(cue.text) == said


def echoes(cues: list[Cue]) -> set[int]:
    """The lines shown as they were said, when they are the odd ones among the lines long
    enough to tell."""
    told = [k for k, cue in enumerate(cues) if len(tokens(cue.source)) >= ECHO]
    same = {k for k in told if as_said(cues[k])}
    return same if len(same) < FEW * len(told) else set()


def shortened(cues: list[Cue]) -> set[int]:
    """The lines much shorter for their speech than the clip's own usual."""
    ratios = {k: letters(cue.text) / max(1, letters(cue.source)) for k, cue in enumerate(cues)
              if len(tokens(cue.source)) >= TOLD and not as_said(cue)}
    if len(ratios) < USUAL:
        return set()
    least = SHORT * median(ratios.values())
    return {k for k, ratio in ratios.items() if ratio < least}


def unfaithful(cues: list[Cue], glossary: Glossary) -> list[int]:
    """The numbers (from 1) of the lines whose translation fails a check; a line with no
    translation is left to its own note (findings.py)."""
    written = [cue for cue in cues if cue.text.strip()]
    odd = echoes(written) | shortened(written)
    failed = {id(cue) for k, cue in enumerate(written)
              if k in odd or lost_number(cue) or misnamed(cue, glossary)}
    return [number for number, cue in enumerate(cues, start=1) if id(cue) in failed]
