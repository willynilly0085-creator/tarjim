import re

from tarjim.prefs.model import Translate

MARKS = ("A", "B", "C", "D")
MARK = re.compile(r"^\s*[\[(]\s*([A-D])\s*[\])]\s*[-–—]?\s*")

EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str, arabic: bool = True, manner: Translate | None = None) -> str:
    """The digits and the paired ?! as the person chose them (translate.numbers and
    translate.question_marks). Until 2026-11-14 eastern digits were turned back to 0-9 and ?!
    was made one mark whatever was chosen, so those two choices did nothing."""
    if arabic and (manner is None or manner.numbers != "eastern"):
        text = text.translate(EASTERN_DIGITS)
    if manner is None or manner.question_marks == "collapse":
        question = "؟" if arabic else "?"
        text = text.replace("؟!", "؟").replace("!؟", "؟").replace("?!", question)
    return " ".join(text.split())


def map_results(items: list[object], count: int, arabic: bool = True,
                manner: Translate | None = None) -> dict[int, str]:
    results: dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        number, text = line_number(item.get("id")), item.get("text")
        if 1 <= number <= count and isinstance(text, str):
            results[number] = normalize(in_order(text), arabic, manner)
    return results


def line_number(value: object) -> int:
    """Models sometimes write the number as "3" or 3.0."""
    try:
        number = float(str(value))
    except ValueError:
        return 0
    return int(number) if number.is_integer() else 0


def over_budget(results: dict[int, str], budgets: list[list[int]]) -> list[int]:
    return [n for n, text in results.items() if too_long(text, budgets[n - 1])]


def too_long(text: str, budgets: list[int]) -> bool:
    """Measured the way the prompt asked (prompt.format_item): an exchange part by part against
    its own budget, the " || " between them not counted, and one sentence for it against the sum.
    Until 2026-11-08 the whole text was measured against the whole cue's budget, so an exchange
    that kept each part's budget was listed as too long."""
    parts = [part.strip() for part in text.split("||")]
    if len(parts) != len(budgets):
        return len(" ".join(part for part in parts if part)) > sum(budgets)
    return any(len(part) > most for part, most in zip(parts, budgets, strict=True))


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
