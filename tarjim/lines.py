import re
import unicodedata

from tarjim.rules import DEFAULT_RULES, Rules

SEPARATOR = "||"
DASH = "- "  # the default of rules.dash, the person's choice since 2026-11-09
LEADING_DASH = re.compile(r"^\s*[-–—]\s*")
CLAUSE_END = ("،", ",", ".", "؟", "?", "!", "؛", ":", "。", "，", "、", "！", "？", "：")
CLAUSE_BONUS = 12
OVERFLOW_PENALTY = 1000
MIN_UNITS = 2
NO_LINE_START = set("、。，．？！：；ー）」』ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ")
INSIDE_A_WORD = {("kanji", "kanji"): 30, ("kanji", "hiragana"): 20,
                 ("katakana", "katakana"): 30, ("hiragana", "hiragana"): 6}
SCRIPTS = (("hiragana", 0x3040, 0x309F), ("katakana", 0x30A0, 0x30FF),
           ("kanji", 0x4E00, 0x9FFF), ("kanji", 0x3400, 0x4DBF))
MARKS = {"Mn", "Mc", "Me"}
JOINER = "\u200d"  # zero width joiner: the letters on both sides are drawn as one
SPACING_MARKS = set("\u0e33\u0eb3")  # Thai and Lao SARA AM: drawn on the letter before
LEADING_VOWELS = set("\u0e40\u0e41\u0e42\u0e43\u0e44\u0ec0\u0ec1\u0ec2\u0ec3\u0ec4")


def script_of(char: str) -> str:
    point = ord(char)
    return next((name for name, low, high in SCRIPTS if low <= point <= high), "other")


def join_penalty(before: str, after: str) -> int:
    if after in NO_LINE_START:
        return OVERFLOW_PENALTY
    return INSIDE_A_WORD.get((script_of(before), script_of(after)), 0)


def text_parts(text: str) -> list[str]:
    """The parts of an exchange as the translation wrote them ("a || b"), empty ones left out;
    none for a text with no separator, which is one translation however it is wrapped."""
    if SEPARATOR not in text:
        return []
    parts = [" ".join(LEADING_DASH.sub("", p).split()) for p in text.split(SEPARATOR)]
    return [part for part in parts if part]


def display_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    if SEPARATOR not in text:
        return balance_lines(text, rules)
    return [rules.dash + part for part in text_parts(text)]


def balance_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= rules.line_chars or rules.max_lines == 1:  # one line asked (2026-11-09)
        return [text]
    joiner = " " if rules.spaced else ""
    units = text.split(" ") if rules.spaced else clusters(text)
    if len(units) < MIN_UNITS:  # one word longer than a line (a link, a handle) stays whole
        return [text]

    def cost(index: int) -> float:
        top, bottom = joiner.join(units[:index]), joiner.join(units[index:])
        overflow = OVERFLOW_PENALTY if max(len(top), len(bottom)) > rules.line_chars else 0
        bonus = CLAUSE_BONUS if units[index - 1].endswith(CLAUSE_END) else 0
        seam = 0 if rules.spaced else join_penalty(units[index - 1][-1], units[index][0])
        return abs(len(top) - len(bottom)) - bonus + overflow + seam

    best = min(range(1, len(units)), key=cost)
    return [joiner.join(units[:best]).strip(), joiner.join(units[best:]).strip()]


def clusters(text: str) -> list[str]:
    """The letters of an unspaced script as they are drawn: a vowel or tone mark stays on its
    letter and a Thai or Lao leading vowel on the letter after it. Before 2026-11-08 a Thai
    line could start with a mark torn from the letter that carries it."""
    found: list[str] = []
    for char in text:
        if found and bound(found[-1], char):
            found[-1] += char
        else:
            found.append(char)
    return found


def bound(before: str, char: str) -> bool:
    """Whether char belongs to the cluster before it."""
    if unicodedata.category(char) in MARKS or char in SPACING_MARKS or char == JOINER:
        return True
    return before[-1] in LEADING_VOWELS or before[-1] == JOINER
