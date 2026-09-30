"""The bot speaks the language the person chose for tarjim's interface."""
import json
from functools import cache

from tarjim.config import setting
from tarjim.ui_languages import FOLDER

FALLBACK = "en"


@cache
def table(code: str) -> dict[str, str]:
    path = FOLDER / f"{code}.json"
    if not path.is_file():
        return {}
    return {k: str(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}


def say(key: str, **values: object) -> str:
    text = table(setting("ui_language") or FALLBACK).get(key) or table(FALLBACK).get(key, key)
    for name, value in values.items():
        text = text.replace(f"{{{name}}}", str(value))
    return text


def result_name(mode: str) -> str:
    if not mode.startswith("dub-"):
        return say("outputSrt" if mode == "srt" else "outputBurn")
    voice = {"gemini": "voiceNatural", "clone": "voiceClone", "studio": "voiceStudio",
             "fish": "voiceFish", "fishvoice": "voiceNarrator"}.get(mode[4:], "voiceNatural")
    return f"{say('outputDub')} · {say(voice)}"
