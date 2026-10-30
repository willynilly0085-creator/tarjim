"""Rewrite subtitle lines into what a voice should say: pronounceable, voweled, names as heard."""
from dataclasses import replace

from tarjim.dub.lines import Line
from tarjim.engines.choice import asker, chain
from tarjim.translate.clean import line_number

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "say": {"type": "string"}}, "required": ["id", "say"]}}
WORDS_PER_SECOND = 2.4  # VoxCPM2 speaking Saudi Arabic, measured 2026-10-30

RULES = """You write the script a text-to-speech voice will read for a dubbed video.
For every numbered line you get: the original speech, its {language} subtitle, the seconds
the voice has and how long the speaker talks. Return what the voice should say in
{language}{dialect}.
- Say everything the ORIGINAL speech says. The subtitle is shortened for reading: take its
  wording and terms, but drop nothing the speaker said (their fillers become natural
  {language} fillers). Sound natural when spoken.
- The speaker is seen talking the whole time, so each line lasts as long as they talk: about
  the number of words given, never far fewer (a short line leaves the voice silent while their
  lips still move) and never more than the voice's seconds allow.
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


def words_for(line: Line) -> int:
    return max(1, round(line.talk * WORDS_PER_SECOND))


def prompt(lines: list[Line], language: str, dialect: str, full_vowels: bool) -> str:
    arabic = language == "Arabic"
    head = RULES.format(language=language,
                        dialect=f" ({dialect} dialect)" if arabic and dialect else "",
                        vowels=(VOWELS if full_vowels else HINTS) if arabic else "")
    body = "\n".join(f"{n}. original: {line.source}\n   subtitle: {line.text}\n"
                     f"   seconds: {line.room:.1f}; the speaker talks for {line.talk:.1f} seconds:"
                     f" about {words_for(line)} words" for n, line in enumerate(lines, start=1))
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
