import re
from typing import Any

MARKS = re.compile("[ً-ْٰ]")
LETTERS = re.compile("[ء-يٱ-ۓ]+")

Prepared = tuple[list[str], list[int], list[str]] | None


def prepare(text: str) -> Prepared:
    tokens = text.split()
    places, cores = [], []
    for index, token in enumerate(tokens):
        runs = LETTERS.findall(MARKS.sub("", token))
        if len(runs) > 1:
            return None
        if runs:
            places.append(index)
            cores.append(runs[0])
    return (tokens, places, cores) if cores else None


def merge(prepared: tuple[list[str], list[int], list[str]], voweled: str) -> str:
    tokens, places, cores = prepared
    words = voweled.split()
    if len(words) != len(cores):
        return " ".join(tokens)
    result = list(tokens)
    for place, core, word in zip(places, cores, words, strict=True):
        if MARKS.sub("", word) == core:
            result[place] = MARKS.sub("", tokens[place]).replace(core, word, 1)
    return " ".join(result)


def add_vowels(texts: list[str], model: Any = None) -> list[str]:
    prepared = [prepare(text) for text in texts]
    batch = [" ".join(p[2]) for p in prepared if p]
    if not batch:
        return texts
    try:
        if model is None:
            from catt_tashkeel import CATTEncoderOnly

            model = CATTEncoderOnly()
        voweled = iter(model.do_tashkeel_batch(batch, verbose=False))
    except Exception:
        return texts
    return [merge(p, next(voweled)) if p else text for p, text in zip(prepared, texts, strict=True)]
