"""Put the same language bar under the title of every translated document.

English lives at the repository root; every other language has its own folder in i18n/.
Each document carries a `<!-- languages -->` line; the bar is written on the line after it.
Run after adding or editing a translation: python scripts/language_bar.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = "<!-- languages -->"
DOCUMENTS = ("README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE.md")
LANGUAGES = {"en": "English", "ar": "العربية", "es": "Español", "fr": "Français",
             "pt": "Português", "de": "Deutsch", "ru": "Русский", "tr": "Türkçe",
             "hi": "हिन्दी", "ur": "اردو", "id": "Bahasa Indonesia", "ja": "日本語",
             "zh": "中文", "ko": "한국어"}


def location(code: str, document: str) -> Path:
    if code == "en":
        return ROOT / ("LICENSE" if document == "LICENSE.md" else document)
    return ROOT / "i18n" / code / document


def bar(current: str, document: str) -> str:
    here = location(current, document).parent
    links = []
    for code, name in LANGUAGES.items():
        target = location(code, document)
        if code == current:
            links.append(f"**{name}**")
        elif target.exists():
            relative = Path(*[".."] * len(here.relative_to(ROOT).parts), target.relative_to(ROOT))
            links.append(f"[{name}]({relative.as_posix()})")
    return " · ".join(links)


def mark(path: Path, line: str) -> None:
    rows = path.read_text(encoding="utf-8").split("\n")
    at = rows.index(MARK)
    if at + 1 < len(rows) and rows[at + 1] and "·" in rows[at + 1]:
        rows[at + 1] = line
    else:
        rows.insert(at + 1, line)
    path.write_text("\n".join(rows), encoding="utf-8", newline="\n")


def main() -> None:
    for document in DOCUMENTS:
        for code in LANGUAGES:
            path = location(code, document)
            if path.exists() and MARK in path.read_text(encoding="utf-8").split("\n"):
                mark(path, bar(code, document))


if __name__ == "__main__":
    main()
