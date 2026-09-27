"""Terms the person wants translated one fixed way: product names, people, places.

One entry per line, "term = translation". Start a line with a language code to limit it to
that language, e.g. "ar: tarjim = ترجم"; lines without a code apply to every language.
"""
import re

from tarjim.config import setting

MAX_TERMS = 50
LIMIT = 200
TAGGED = re.compile(r"^\s*([a-z]{2,3}(?:-[a-z]{2,4})?)\s*:\s*(.+)$", re.IGNORECASE)

Glossary = tuple[tuple[str, str], ...]


def language_code(language: str) -> str:
    from tarjim.languages import LANGUAGES

    wanted = language.strip().lower()
    return next((code for code, lang in LANGUAGES.items() if lang.name.lower() == wanted), wanted)


def entry_for(line: str, language: str) -> tuple[str, str] | None:
    tagged = TAGGED.match(line)
    if tagged:
        if language and tagged.group(1).lower() != language:
            return None
        line = tagged.group(2)
    term, sep, meaning = line.partition("=")
    if not (sep and term.strip() and meaning.strip()):
        return None
    return term.strip()[:LIMIT], meaning.strip()[:LIMIT]


def parse(text: str, language: str = "") -> Glossary:
    code = language_code(language) if language else ""
    entries = (entry_for(line, code) for line in text.replace(";", "\n").splitlines())
    return tuple(e for e in entries if e)[:MAX_TERMS]


def current(language: str = "") -> Glossary:
    return parse(setting("glossary"), language)


def instructions(glossary: Glossary) -> str:
    if not glossary:
        return ""
    lines = "\n".join(f"- {term} → {meaning}" for term, meaning in glossary)
    return f"\n\nAlways translate these terms exactly as given (names, brands):\n{lines}"
