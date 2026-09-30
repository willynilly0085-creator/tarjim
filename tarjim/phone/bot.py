"""Read the bot's messages and turn a link (or a small video) from the paired account into a job.

Anyone else is ignored. Pairing needs a one-time code that only the computer's settings page shows,
and that code is only good for a few minutes.
"""
import json
import re
import secrets
import time
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.phone.links import first_link
from tarjim.phone.progress import Follower
from tarjim.phone.telegram import FETCH_LIMIT, Bot, TelegramError
from tarjim.phone.words import result_name, say

CODE_SECONDS = 15 * 60
MODES = ("burn", "srt", "dub-gemini", "dub-clone", "dub-studio")
SAFE = re.compile(r"[^\w.-]")


class Pairing:
    def __init__(self) -> None:
        self.code, self.until = "", 0.0

    def fresh(self) -> str:
        self.code, self.until = secrets.token_urlsafe(12), time.time() + CODE_SECONDS
        return self.code

    def take(self, offered: str) -> bool:
        good = bool(self.code) and time.time() < self.until and secrets.compare_digest(
            offered, self.code)
        if good:
            self.code = ""
        return good


def owner() -> int:
    return int(setting("phone_chat") or 0)


def order_for(source: str, name: str = "") -> Any:
    from tarjim.server.jobs import Order

    return Order(source, setting("phone_target") or "ar", setting("phone_mode") or "burn",
                 setting("phone_dialect") or "saudi", name)


def modes_keyboard() -> str:
    current = setting("phone_mode") or "burn"
    rows = [[{"text": ("✓ " if mode == current else "") + result_name(mode),
              "callback_data": f"mode:{mode}"}] for mode in MODES]
    return json.dumps({"inline_keyboard": rows})


class Inbox:
    def __init__(self, follower: Follower, uploads: Path, pairing: Pairing) -> None:
        self.follower, self.uploads, self.pairing = follower, uploads, pairing

    def handle(self, bot: Bot, update: dict[str, Any]) -> None:
        if "callback_query" in update:
            self.pressed(bot, update["callback_query"])
            return
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private":
            return
        text = str(message.get("text") or "")
        if text.startswith("/start"):
            self.start(bot, int(chat["id"]), text.partition(" ")[2].strip())
        elif int(chat["id"]) == owner():
            self.from_owner(bot, int(chat["id"]), message, text)

    def start(self, bot: Bot, chat: int, code: str) -> None:
        if chat == owner():
            bot.say(chat, say("phone_welcome"))
        elif not owner() and code and self.pairing.take(code):
            save("phone_chat", str(chat))
            bot.say(chat, say("phone_welcome"))
        elif not owner():
            bot.say(chat, say("phone_bad_code"))

    def from_owner(self, bot: Bot, chat: int, message: dict[str, Any], text: str) -> None:
        if text.startswith("/mode"):
            bot.say(chat, say("phone_mode_title"), reply_markup=modes_keyboard())
            return
        video = message.get("video") or message.get("document") or {}
        link = first_link(message)
        if link:
            self.follower.watch(bot, chat, self.follower.jobs.submit(order_for(link)))
        elif str(video.get("mime_type", "")).startswith("video/"):
            self.take_file(bot, chat, video)
        else:
            bot.say(chat, say("phone_help"))

    def take_file(self, bot: Bot, chat: int, video: dict[str, Any]) -> None:
        if int(video.get("file_size") or 0) > FETCH_LIMIT:
            bot.say(chat, say("phone_file_big"))
            return
        name = SAFE.sub("_", str(video.get("file_name") or "telegram-video.mp4"))[-80:]
        folder = self.uploads / f"telegram-{secrets.token_hex(6)}"
        folder.mkdir(parents=True, exist_ok=True)
        bot.fetch(str(video["file_id"]), folder / name)
        self.follower.watch(bot, chat, self.follower.jobs.submit(order_for(str(folder / name),
                                                                           name)))

    def pressed(self, bot: Bot, press: dict[str, Any]) -> None:
        chat = int((press.get("message") or {}).get("chat", {}).get("id", 0))
        kind, _, value = str(press.get("data", "")).partition(":")
        if chat != owner() or chat == 0:
            return
        if kind == "mode" and value in MODES:
            save("phone_mode", value)
            bot.edit(chat, int(press["message"]["message_id"]),
                     say("phone_mode_saved", mode=result_name(value)))
        elif kind == "cancel" and re.fullmatch(r"[0-9a-f]{12}", value):
            self.follower.jobs.steer(value, "cancel", "telegram")
        try:
            bot.call("answerCallbackQuery", callback_query_id=press["id"])
        except TelegramError:
            return
