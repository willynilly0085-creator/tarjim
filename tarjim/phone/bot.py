"""Read the bot's messages and turn a link (or a small video) from the paired account into a job.

Anyone else is ignored. Pairing needs a one-time code that only the computer's settings page shows,
and that code is only good for a few minutes.
"""
import contextlib
import re
import secrets
import time
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.phone import large
from tarjim.phone.choice import MODES, Waiting, choices_keyboard, modes_keyboard
from tarjim.phone.links import first_link
from tarjim.phone.meter import shown
from tarjim.phone.progress import Follower
from tarjim.phone.telegram import FETCH_LIMIT, Bot, TelegramError
from tarjim.phone.words import result_name, say
from tarjim.server.guard import safe_name

CODE_SECONDS = 15 * 60
SAFE = re.compile(r"[^\w.-]")


class Pairing:
    def __init__(self) -> None:
        self.code, self.until = "", 0.0

    def fresh(self) -> str:
        self.code, self.until = secrets.token_urlsafe(12), time.time() + CODE_SECONDS
        return self.code

    def take(self, offered: str) -> bool:
        good = bool(self.code) and time.time() < self.until and secrets.compare_digest(
            offered.encode(), self.code.encode())
        if good:
            self.code = ""
        return good


def owner() -> int:
    return int(setting("phone_chat") or 0)


def order_for(source: str, name: str, mode: str) -> Any:
    from tarjim.server.jobs import Order

    return Order(source, setting("phone_target") or "ar", mode, setting("phone_dialect") or "saudi",
                 name)


class Inbox:
    def __init__(self, follower: Follower, uploads: Path, pairing: Pairing) -> None:
        self.follower, self.uploads, self.pairing = follower, uploads, pairing
        self.waiting = Waiting()

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
            self.ask(bot, chat, {"source": link, "name": ""})
        elif str(video.get("mime_type", "")).startswith("video/"):
            self.ask_file(bot, chat, {**video, "message": int(message.get("message_id") or 0)})
        else:
            bot.say(chat, say("phone_help"))

    def ask(self, bot: Bot, chat: int, item: dict[str, Any]) -> None:
        bot.say(chat, say("phone_choose"), reply_markup=choices_keyboard(self.waiting.keep(item)))

    def ask_file(self, bot: Bot, chat: int, video: dict[str, Any]) -> None:
        size = int(video.get("file_size") or 0)
        big = size > FETCH_LIMIT
        if big and (not large.ready() or size > large.LIMIT):
            bot.say(chat, say("phone_file_huge" if large.ready() else "phone_file_big"))
            return
        named = safe_name(str(video.get("file_name") or "")) or "telegram-video.mp4"
        name = SAFE.sub("_", named)[-80:]
        self.ask(bot, chat, {"file_id": str(video["file_id"]), "name": name, "chat": chat,
                             "message": video["message"] if big else 0})

    def fetched(self, bot: Bot, item: dict[str, Any]) -> str:
        if "file_id" not in item:
            return str(item["source"])
        folder = self.uploads / f"telegram-{secrets.token_hex(6)}"
        folder.mkdir(parents=True, exist_ok=True)
        def tell(done: int, total: int) -> None:
            bot.edit(item["chat"], item["status"], shown(say("stage_downloading"), done, total))

        if item.get("message"):
            large.fetch(item["chat"], item["message"], folder / item["name"], tell)
        else:
            bot.fetch(item["file_id"], folder / item["name"], tell)
        return str(folder / item["name"])

    def start_choice(self, bot: Bot, chat: int, message: int, choice: str) -> None:
        mode, _, key = choice.partition(":")
        item = self.waiting.take(key) if mode in MODES else None
        if item is None:
            bot.edit(chat, message, say("phone_choice_expired"))
            return
        save("phone_mode", mode)
        if "file_id" in item:
            item["status"] = message
            bot.edit(chat, message, say("stage_downloading"))
        try:
            source = self.fetched(bot, item)
        except (TelegramError, OSError):
            bot.edit(chat, message, say("phone_fetch_failed"))
            return
        task = self.follower.jobs.submit(order_for(source, item["name"], mode))
        self.follower.adopt(bot, chat, message, task)

    def pressed(self, bot: Bot, press: dict[str, Any]) -> None:
        chat = int((press.get("message") or {}).get("chat", {}).get("id", 0))
        kind, _, value = str(press.get("data", "")).partition(":")
        if chat != owner() or chat == 0:
            return
        with contextlib.suppress(TelegramError):
            bot.call("answerCallbackQuery", callback_query_id=press["id"])
        message = int(press["message"]["message_id"])
        if kind == "go":
            self.start_choice(bot, chat, message, value)
        elif kind == "mode" and value in MODES:
            save("phone_mode", value)
            bot.edit(chat, message, say("phone_mode_saved", mode=result_name(value)))
        elif kind == "cancel" and re.fullmatch(r"[0-9a-f]{12}", value):
            self.follower.jobs.steer(value, "cancel", "telegram")
