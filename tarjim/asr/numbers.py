"""What a number in a line sounds like, so the aligner can find it in the sound.

The aligner hears letters only, and a "2" has none: on 2026-10-31 a Russian countdown,
"Осталось 3 секунды, 2, 1, 0!", came out with "2" on screen for six seconds and "1, 0!" glued
to the next sentence, because none of the three could be placed. So a number is spelled out in
the language that was heard ("два"), and "4 000" is one number ("четыре тысячи"), not "four
zero". A language num2words does not know keeps its digits, and fill_gaps shares their time.
"""
import re

from tarjim.translate.glossary import language_code

GROUPED = re.compile(r"\d{1,3}(?:[ ,.  ]\d{3})+")  # 4,000 · 4 000 · 4.000
DIGITS = re.compile(r"\d+")
THOUSANDS = re.compile(r"\d{3}\W*")  # a word of its own that goes on the number before it


def spell(text: str, code: str) -> str:
    from num2words import num2words

    def one(match: re.Match[str]) -> str:
        try:
            return str(num2words(int(match.group()), lang=code))
        except (NotImplementedError, OverflowError, ValueError):
            return match.group()

    joined = GROUPED.sub(lambda m: re.sub(r"\D", "", m.group()), text)
    return DIGITS.sub(one, joined)


def joined(texts: list[str]) -> list[str]:
    """Each word, with a group of three digits moved onto the number it belongs to."""
    out, owner = list(texts), -1
    for k, text in enumerate(texts):
        if owner >= 0 and THOUSANDS.fullmatch(text) and out[owner][-1:].isdigit():
            out[owner], out[k] = out[owner] + text, ""
        else:
            owner = k
    return out


def said(texts: list[str], language: str) -> list[str]:
    """What each word sounds like; "" for a word said as part of the one before it."""
    if not any(DIGITS.search(text) for text in texts):
        return texts
    try:
        import num2words  # noqa: F401  # installed with tarjim; an older install may lack it
    except ImportError:
        return texts
    code = language_code(language)
    return [spell(text, code) for text in joined(texts)]
