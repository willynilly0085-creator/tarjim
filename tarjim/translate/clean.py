from tarjim.rules import DEFAULT_RULES, Rules

EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str, arabic: bool = True) -> str:
    if arabic:
        text = text.translate(EASTERN_DIGITS)
    question = "؟" if arabic else "?"
    text = text.replace("؟!", "؟").replace("!؟", "؟").replace("?!", question)
    return " ".join(text.split())


def map_results(items: list[dict[str, object]], count: int,
                arabic: bool = True) -> dict[int, str]:
    results: dict[int, str] = {}
    for item in items:
        number = item.get("id")
        text = item.get("text")
        if isinstance(number, int) and 1 <= number <= count and isinstance(text, str):
            results[number] = normalize(text, arabic)
    return results


def over_budget(results: dict[int, str], budgets: list[int]) -> list[int]:
    return [n for n, text in results.items() if len(text) > budgets[n - 1]]


def budgets_for(durations: list[float], rules: Rules = DEFAULT_RULES) -> list[int]:
    return [rules.char_budget(d) for d in durations]
