from tarjim.rules import DEFAULT_RULES, Rules

SEPARATOR = "||"
DASH = "- "
CLAUSE_END = ("،", ",", ".", "؟", "?", "!", "؛", ":", "。", "，", "、", "！", "？", "：")
CLAUSE_BONUS = 12
OVERFLOW_PENALTY = 1000


def display_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    if SEPARATOR not in text:
        return balance_lines(text, rules)
    parts = [" ".join(p.replace(DASH.strip(), "", 1).split()) for p in text.split(SEPARATOR)]
    return [DASH + part for part in parts if part]


def balance_lines(text: str, rules: Rules = DEFAULT_RULES) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= rules.line_chars:
        return [text]
    joiner = " " if rules.spaced else ""
    units = text.split(" ") if rules.spaced else list(text)

    def cost(index: int) -> float:
        top, bottom = joiner.join(units[:index]), joiner.join(units[index:])
        overflow = OVERFLOW_PENALTY if max(len(top), len(bottom)) > rules.line_chars else 0
        bonus = CLAUSE_BONUS if units[index - 1].endswith(CLAUSE_END) else 0
        return abs(len(top) - len(bottom)) - bonus + overflow

    best = min(range(1, len(units)), key=cost)
    return [joiner.join(units[:best]).strip(), joiner.join(units[best:]).strip()]
