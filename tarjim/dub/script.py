"""Rewrite subtitle lines into what a voice should say: pronounceable, voweled, names as heard."""
from dataclasses import replace

from tarjim.dub.lines import Line
from tarjim.engines.choice import asker, chain
from tarjim.translate.clean import line_number

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "say": {"type": "string"}}, "required": ["id", "say"]}}
WORDS_PER_SECOND = 2.6

RULES = """You write the script a text-to-speech voice will read for a dubbed video.
For every numbered line you get: the original speech, its {language} subtitle, and the seconds
the voice has. Return what the voice should say in {language}{dialect}.
- Keep the meaning of the subtitle. Sound natural when spoken, and fit the seconds
  (about {pace} words per second at most).
- Names, brands, apps and foreign words: take them from the ORIGINAL speech, never from the
  subtitle (its spelling can be wrong), and write them in {language} letters exactly as they
  are pronounced (for example Pocketflow is said "bo-ket flo", PayPal "pay pal").
- Numbers, prices, currencies, symbols and abbreviations: write them as spoken words.
- Only the words to say: no quotes, no notes, no stage directions.{vowels}
"""
VOWELS = ("\n- Put full Arabic diacritics (tashkeel) on every word, the way it is pronounced in"
          " the dialect, so the voice cannot misread any word.")
HINTS = ("\n- Add diacritics only on a letter the voice could misread (a name, or a word whose"
         " meaning changes with its vowels). Leave the rest plain, as people write the dialect.")


def prompt(lines: list[Line], language: str, dialect: str, full_vowels: bool) -> str:
    arabic = language == "Arabic"
    head = RULES.format(language=language, pace=WORDS_PER_SECOND,
                        dialect=f" ({dialect} dialect)" if arabic and dialect else "",
                        vowels=(VOWELS if full_vowels else HINTS) if arabic else "")
    body = "\n".join(f"{n}. original: {line.source}\n   subtitle: {line.text}\n"
                     f"   seconds: {line.room:.1f}" for n, line in enumerate(lines, start=1))
    from tarjim.translate.glossary import current, instructions

    return f"{head}{instructions(current(language))}\n{body}"


def spoken_lines(lines: list[Line], language: str, dialect: str,
                 full_vowels: bool = True) -> list[Line] | None:
    if not lines:
        return lines
    for provider in chain("translate"):
        try:
            answer = asker(provider).ask(prompt(lines, language, dialect, full_vowels), None,
                                         SCHEMA)
        except Exception:
            continue
        said = {line_number(item.get("id")): str(item.get("say", "")).strip()
                for item in answer or [] if isinstance(item, dict)}
        if all(said.get(n) for n in range(1, len(lines) + 1)):
            return [replace(line, text=said[n]) for n, line in enumerate(lines, start=1)]
    return None
