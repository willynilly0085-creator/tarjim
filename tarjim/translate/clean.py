from tarjim.rules import DEFAULT_RULES, Rules

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
            results[number] = normalize(text, arabic)
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
