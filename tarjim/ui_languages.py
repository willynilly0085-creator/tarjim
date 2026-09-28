"""Interface languages: one file per language in tarjim/web/i18n, each naming itself."""
import json
from functools import cache
from pathlib import Path

FOLDER = Path(__file__).resolve().parent / "web" / "i18n"
ORDER = ("en", "ar", "es", "fr", "pt", "de", "ru", "tr", "hi", "ur", "id", "ja", "zh", "ko")


@cache
def available() -> tuple[dict[str, str], ...]:
    found = {}
    for path in FOLDER.glob("*.json"):
        words = json.loads(path.read_text(encoding="utf-8"))
        found[path.stem] = {"code": path.stem, "name": str(words.get("languageName", path.stem)),
                            "dir": str(words.get("dir", "ltr"))}
    rank = {code: at for at, code in enumerate(ORDER)}
    return tuple(found[code] for code in sorted(found, key=lambda c: (rank.get(c, len(ORDER)), c)))


def codes() -> tuple[str, ...]:
    return tuple(language["code"] for language in available())
