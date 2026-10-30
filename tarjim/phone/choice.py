"""Ask what the person wants for each link or video before starting it: subtitles in the video, a
subtitle file, or dubbing, then for Arabic whether Saudi or standard. The last choice is offered
first, marked, one tap away."""
import json
import secrets
import threading
from typing import Any

from tarjim.config import SPOKEN, api_key, setting
from tarjim.phone.words import result_name, say

LINKED = {"dub-eleven": "eleven_api_key", "dub-elevenclone": "eleven_api_key",
          "dub-speech": "speech_api_key"}
MODES = ("burn", "srt", "dub-gemini", "dub-clone", "dub-studio", *LINKED)
# A voice that needs a key is offered once the key is there: without it the natural voice would
# quietly become the cloned one (dub/make.py choose).
KEYED = {"dub-gemini": SPOKEN, **LINKED}
DIALECTS = {"saudi": "dialectSaudi", "msa": "dialectMsa"}
KEEP = 50


class Waiting:
    """Links and videos waiting for a choice, by a short key that fits in a button."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def keep(self, item: dict[str, Any]) -> str:
        key = secrets.token_hex(4)
        with self.lock:
            self.items[key] = item
            while len(self.items) > KEEP:
                self.items.pop(next(iter(self.items)))
        return key

    def has(self, key: str) -> bool:
        with self.lock:
            return key in self.items

    def peek(self, key: str) -> dict[str, Any] | None:
        with self.lock:
            return self.items.get(key)

    def mark(self, key: str, **values: Any) -> bool:
        """Keep a choice with a waiting item; False when the item is gone."""
        with self.lock:
            found = key in self.items
            if found:
                self.items[key].update(values)
            return found

    def take(self, key: str) -> dict[str, Any] | None:
        with self.lock:
            return self.items.pop(key, None)


def offered() -> list[str]:
    """Voices that need the person's own key are offered once that key is saved."""
    return [mode for mode in MODES if mode not in KEYED or api_key(KEYED[mode])]


def ordered_modes() -> list[str]:
    current, modes = setting("phone_mode") or "burn", offered()
    return [current, *[m for m in modes if m != current]] if current in modes else modes


def label(mode: str, current: str) -> str:
    return ("✓ " if mode == current else "") + result_name(mode)


def choices_keyboard(key: str) -> str:
    current = setting("phone_mode") or "burn"
    rows = [[{"text": label(mode, current), "callback_data": f"go:{mode}:{key}"}]
            for mode in ordered_modes()]
    return json.dumps({"inline_keyboard": rows})


def modes_keyboard() -> str:
    current = setting("phone_mode") or "burn"
    rows = [[{"text": label(mode, current), "callback_data": f"mode:{mode}"}]
            for mode in offered()]
    return json.dumps({"inline_keyboard": rows})


def dialect_keyboard(mode: str, key: str) -> str:
    """Arabic only: Saudi then standard, always in that order, the last one used marked. The
    last one used came first before: the buttons swapped places after each choice, and the owner,
    pressing the same place each time, got Saudi when asking for standard (2026-10-30)."""
    current = setting("phone_dialect") or "saudi"
    rows = [[{"text": ("✓ " if d == current else "") + say(DIALECTS[d]),
              "callback_data": f"dl:{d}:{mode}:{key}"}] for d in DIALECTS]
    return json.dumps({"inline_keyboard": rows})
