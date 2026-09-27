from tarjim.rules import DEFAULT_RULES, Rules

SEPARATOR = "||"
DASH = "- "
CLAUSE_END = ("،", ",", ".", "؟", "?", "!", "؛", ":", "。", "，", "、", "！", "？", "：")
CLAUSE_BONUS = 12
OVERFLOW_PENALTY = 1000
NO_LINE_START = set("、。，．？！：；ー）」』ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ")
INSIDE_A_WORD = {("kanji", "kanji"): 30, ("kanji", "hiragana"): 20,
                 ("katakana", "katakana"): 30, ("hiragana", "hiragana"): 6}
SCRIPTS = (("hiragana", 0x3040, 0x309F), ("katakana", 0x30A0, 0x30FF),
           ("kanji", 0x4E00, 0x9FFF), ("kanji", 0x3400, 0x4DBF))


def script_of(char: str) -> str:
    point = ord(char)
    return next((name for name, low, high in SCRIPTS if low <= point <= high), "other")


def join_penalty(before: str, after: str) -> int:
    if after in NO_LINE_START:
        return OVERFLOW_PENALTY
    return INSIDE_A_WORD.get((script_of(before), script_of(after)), 0)


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
        seam = 0 if rules.spaced else join_penalty(units[index - 1][-1], units[index][0])
        return abs(len(top) - len(bottom)) - bonus + overflow + seam

    best = min(range(1, len(units)), key=cost)
    return [joiner.join(units[:best]).strip(), joiner.join(units[best:]).strip()]
