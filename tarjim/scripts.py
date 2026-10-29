"""Words of scripts written without spaces between them (Chinese, Japanese, Thai, Lao, Khmer,
Burmese). Split on spaces alone, a whole sentence becomes one word: one huge subtitle, timed as
one block. Each character is a word instead, as the local aligner (Qwen3-ForcedAligner) times
Chinese; a combining mark and punctuation stay with the character before them."""
import re

UNSPACED = re.compile("[฀-໿က-႟ក-៿぀-ヿ㐀-䶿"
                      "一-鿿豈-﫿]")


def joins(unit: str, char: str) -> bool:
    if not char.isalnum() or not any(c.isalnum() for c in unit):
        return True  # a mark or punctuation, or the character after an opening quote
    last = unit[-1]
    return not UNSPACED.match(char) and last.isalnum() and not UNSPACED.match(last)


def split_token(token: str) -> list[str]:
    if not UNSPACED.search(token):
        return [token]
    units: list[str] = []
    for char in token:
        if units and joins(units[-1], char):
            units[-1] += char
        else:
            units.append(char)
    return units


def split_words(text: str) -> list[str]:
    return [unit for token in text.split() for unit in split_token(token)]


def joined(texts: list[str]) -> str:
    """Words back into text: a space between them, except between two unspaced ones."""
    result, previous = "", ""
    for text in texts:
        tight = UNSPACED.search(previous) and UNSPACED.search(text)
        result += text if tight or not result else f" {text}"
        previous = text
    return result.strip()
