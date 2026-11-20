"""What a person chose in the browser add-on (language, dialect, what comes out, voice, how
selected text is translated), kept by the engine as well.

Each browser keeps its add-on's choices to itself, so a browser added later started with the
defaults: on 2026-11-20 the owner's Firefox on his new Mac offered a Saudi dialect, Gemini's
voice and the right-click menu, while his Chrome on Windows had standard Arabic, studio voices
and a button by selected text. The add-on now tells the engine each choice it saves, and a
browser that joins takes what the engine kept (tarjim/extension/pairing.js, shareChoices).
"""
import json
import re

from tarjim.config import save, setting

KEPT = ("target", "dialect", "mode", "voice", "textMode", "textOther")
VALUE = re.compile(r"^[\w-]{0,40}$")
NAME = "browser_choices"


def read() -> dict[str, str]:
    try:
        found = json.loads(setting(NAME) or "{}")
    except ValueError:
        return {}
    return clean(found) if isinstance(found, dict) else {}


def clean(given: dict[str, object]) -> dict[str, str]:
    """Only the choices the add-on has, each a short plain word; anything else is dropped."""
    return {key: str(given[key]) for key in KEPT
            if isinstance(given.get(key), str) and VALUE.match(str(given[key]))}


def remember(given: dict[str, object]) -> dict[str, str]:
    kept = {**read(), **clean(given)}
    save(NAME, json.dumps(kept, sort_keys=True))
    return kept
