from tarjim.rules import DEFAULT_RULES, Rules

SEPARATOR = "||"
DASH = "- "
CLAUSE_END = ("،", ",", ".", "؟", "?", "!", "؛", ":")


def display_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    if SEPARATOR not in text:
        return balance_lines(text, rules)
    parts = [" ".join(p.replace(DASH.strip(), "", 1).split()) for p in text.split(SEPARATOR)]
    return [DASH + part for part in parts if part]
CLAUSE_BONUS = 12
OVERFLOW_PENALTY = 1000


def balance_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= rules.line_chars:
        return [text]
    words = text.split(" ")
    best = min(range(1, len(words)), key=lambda i: split_cost(words, i, rules.line_chars))
    return [" ".join(words[:best]), " ".join(words[best:])]


def split_cost(words: list[str], index: int, line_chars: int) -> float:
    top = len(" ".join(words[:index]))
    bottom = len(" ".join(words[index:]))
    overflow = OVERFLOW_PENALTY if max(top, bottom) > line_chars else 0
    bonus = CLAUSE_BONUS if words[index - 1].endswith(CLAUSE_END) else 0
    return abs(top - bottom) - bonus + overflow
