"""Terms the person wants translated one fixed way: product names, people, places."""
from tarjim.config import setting

MAX_TERMS = 50
LIMIT = 200

Glossary = tuple[tuple[str, str], ...]


def parse(text: str) -> Glossary:
    pairs = []
    for line in text.replace(";", "\n").splitlines():
        term, sep, meaning = line.partition("=")
        if sep and term.strip() and meaning.strip():
            pairs.append((term.strip()[:LIMIT], meaning.strip()[:LIMIT]))
    return tuple(pairs[:MAX_TERMS])


def current() -> Glossary:
    return parse(setting("glossary"))


def instructions(glossary: Glossary) -> str:
    if not glossary:
        return ""
    lines = "\n".join(f"- {term} → {meaning}" for term, meaning in glossary)
    return f"\n\nAlways translate these terms exactly as given (names, brands):\n{lines}"
