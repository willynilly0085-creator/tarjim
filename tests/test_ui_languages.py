import json
import re
from pathlib import Path

from tarjim.ui_languages import FOLDER, available, codes

PLACEHOLDER = re.compile(r"\{\w+\}")
EXTENSION = Path(__file__).resolve().parents[1] / "extension" / "_locales"


def test_every_interface_language_names_itself_and_arabic_and_urdu_read_right_to_left() -> None:
    assert codes()[:2] == ("en", "ar") and len(codes()) == 14
    names = {language["code"]: language for language in available()}
    assert names["ar"]["name"] == "العربية" and names["ur"]["dir"] == "rtl"
    assert all(language["name"] != language["code"] for language in available())


def test_every_language_file_has_the_english_keys_and_placeholders() -> None:
    english = json.loads((FOLDER / "en.json").read_text(encoding="utf-8"))
    for code in codes():
        words = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        assert list(words) == list(english), code
        for key, text in english.items():
            assert sorted(PLACEHOLDER.findall(str(text))) == sorted(
                PLACEHOLDER.findall(str(words[key]))), (code, key)


def test_the_extension_speaks_the_same_languages() -> None:
    english = json.loads((EXTENSION / "en" / "messages.json").read_text(encoding="utf-8"))
    for code in codes():
        words = json.loads((EXTENSION / code / "messages.json").read_text(encoding="utf-8"))
        assert list(words) == list(english), code
