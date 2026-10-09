"""Ask what the person wants for each link or video before starting it: subtitles in the video, a
subtitle file, or dubbing. The last choice is offered first, marked, one tap away."""
import json
import secrets
import threading
from typing import Any

from tarjim.config import setting
from tarjim.phone.words import result_name

ALWAYS = ("burn", "srt", "dub-gemini", "dub-clone", "dub-studio")
LINKED = {"dub-eleven": "eleven_api_key", "dub-elevenclone": "eleven_api_key",
          "dub-speech": "speech_api_key"}
MODES = (*ALWAYS, *LINKED)
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

    def take(self, key: str) -> dict[str, Any] | None:
        with self.lock:
            return self.items.pop(key, None)


def offered() -> list[str]:
    """Voices that need the person's own key are offered once that key is saved."""
    return [*ALWAYS, *[mode for mode, key in LINKED.items() if setting(key)]]


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
