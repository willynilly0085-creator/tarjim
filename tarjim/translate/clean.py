import re

from tarjim.rules import DEFAULT_RULES, Rules

MARKS = ("A", "B", "C", "D")
MARK = re.compile(r"^\s*[\[(]\s*([A-D])\s*[\])]\s*[-–—]?\s*")

EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str, arabic: bool = True) -> str:
    if arabic:
        text = text.translate(EASTERN_DIGITS)
    question = "؟" if arabic else "?"
    text = text.replace("؟!", "؟").replace("!؟", "؟").replace("?!", question)
    return " ".join(text.split())


def map_results(items: list[object], count: int,
                arabic: bool = True) -> dict[int, str]:
    results: dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        number, text = line_number(item.get("id")), item.get("text")
        if 1 <= number <= count and isinstance(text, str):
            results[number] = normalize(in_order(text), arabic)
    return results


def line_number(value: object) -> int:
    """Models sometimes write the number as "3" or 3.0."""
    try:
        number = float(str(value))
    except ValueError:
        return 0
    return int(number) if number.is_integer() else 0


def over_budget(results: dict[int, str], budgets: list[int]) -> list[int]:
    return [n for n, text in results.items() if len(text) > budgets[n - 1]]


def budgets_for(durations: list[float], rules: Rules = DEFAULT_RULES) -> list[int]:
    return [rules.char_budget(d) for d in durations]


def in_order(text: str) -> str:
    """The parts of an exchange back in the order of their marks ([A] first), marks removed.
    Measured on 2026-10-29: asked for "[A] Right. || [B] somewhere in India.", a model answered
    with India first, so the reply showed in the other speaker's colour and at the wrong moment."""
    parts = [MARK.match(part) for part in text.split("||")]
    bare = [MARK.sub("", part, count=1).strip() for part in text.split("||")]
    marks = [found.group(1) if found else "" for found in parts]
    if len(bare) > 1 and all(marks) and len(set(marks)) == len(marks):
        bare = [part for _mark, part in sorted(zip(marks, bare, strict=True))]
    return " || ".join(bare)
