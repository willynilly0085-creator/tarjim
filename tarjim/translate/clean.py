from tarjim.rules import DEFAULT_RULES, Rules

EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str) -> str:
    text = text.translate(EASTERN_DIGITS)
    text = text.replace("؟!", "؟").replace("!؟", "؟").replace("?!", "؟")
    return " ".join(text.split())


def map_results(items: list[dict[str, object]], count: int) -> dict[int, str]:
    results: dict[int, str] = {}
    for item in items:
        number = item.get("id")
        text = item.get("ar")
        if isinstance(number, int) and 1 <= number <= count and isinstance(text, str):
            results[number] = normalize(text)
    return results


def over_budget(results: dict[int, str], budgets: list[int]) -> list[int]:
    return [n for n, text in results.items() if len(text) > budgets[n - 1]]


def budgets_for(durations: list[float], rules: Rules = DEFAULT_RULES) -> list[int]:
    return [rules.char_budget(d) for d in durations]
