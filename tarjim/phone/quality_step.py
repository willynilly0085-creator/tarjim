"""For a link, after the kind of result: the qualities it offers, as buttons with their sizes.
1080p (or the nearest below it) comes first and ticked; "sound only" is offered for a subtitle
file alone; a quality past the 8 GB limit is left out. Nothing is remembered for the next link
(the owner, 2026-10-24). The pick is kept with the waiting link, so the buttons that follow
(the style of Arabic) stay as short as Telegram needs them."""
import json
from typing import Any

from tarjim import fetch
from tarjim.phone.choice import MODES, Waiting
from tarjim.phone.telegram import Bot
from tarjim.phone.words import say
from tarjim.qualities import AUDIO, clean
from tarjim.server.jobs import classify

MB = 1024 * 1024
Where = tuple[int, int]


def size_text(size: int) -> str:
    if size >= 1024 * MB:
        return say("sizeGb", n=f"{size / (1024 * MB):.1f}")
    return say("phone_size", mb=max(1, round(size / MB)))


def label(name: str, size: int, ticked: bool) -> str:
    shown = say("qualityRow", label=name, size=size_text(size)) if size else name
    return ("✓ " if ticked else "") + shown


def buttons(found: dict[str, Any], sound: bool) -> list[tuple[str, str, int]]:
    """(quality, its name, its size): the default first, then the rest largest first."""
    rows = [(c["id"], c["label"], int(c.get("size") or 0)) for c in found["choices"]]
    rows.sort(key=lambda row: row[0] != found["default"])
    audio = found.get("audio")
    rows += [(AUDIO, say("qualityAudio"), int(audio.get("size") or 0))] if sound and audio else []
    return [row for row in rows if row[2] <= int(found["limit"])]


def quality_keyboard(found: dict[str, Any], mode: str, key: str) -> str:
    rows = [[{"text": label(name, size, quality == found["default"]),
              "callback_data": f"q:{quality}:{mode}:{key}"}]
            for quality, name, size in buttons(found, mode == "srt")]
    return json.dumps({"inline_keyboard": rows})


class QualityStep:
    waiting: Waiting

    def next_step(self, bot: Bot, where: Where, mode: str, key: str) -> None:
        raise NotImplementedError

    def ask_quality(self, bot: Bot, where: Where, mode: str, key: str) -> None:
        item = self.waiting.peek(key) or {}
        bot.edit(*where, say("qualityReading"))
        try:
            found = fetch.look(str(item.get("source", "")))
        except Exception as error:  # yt-dlp raises many kinds; only a list stops the link
            if classify(error) != "list":
                return self.next_step(bot, where, mode, key)
            self.waiting.take(key)
            return bot.edit(*where, say("err_list"))
        if not buttons(found, mode == "srt"):
            return self.next_step(bot, where, mode, key)
        bot.edit(*where, say("phone_choose_quality"),
                 reply_markup=quality_keyboard(found, mode, key))

    def chosen_quality(self, bot: Bot, chat: int, message: int, choice: str) -> None:
        quality, _, rest = choice.partition(":")
        mode, _, key = rest.partition(":")
        if mode in MODES and self.waiting.mark(key, quality=clean(quality)):
            self.next_step(bot, (chat, message), mode, key)
        else:
            bot.edit(chat, message, say("phone_choice_expired"))
