"""After the last choice: check that tarjim can make the order, take a video sent from the phone,
then start the job. A press is handled off the bot's only message thread (in_background), so a
long download from Telegram or a slow quality list never holds up a Cancel or the next link."""
import secrets
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.languages import language
from tarjim.phone import large
from tarjim.phone.choice import MODES, Waiting
from tarjim.phone.meter import shown
from tarjim.phone.progress import Follower
from tarjim.phone.telegram import Bot, TelegramError, note
from tarjim.phone.words import say

# Why an order cannot be made, in the page's own words (web/workspace.js).
REFUSED = {"dub_language": "sendDubLanguage", "dub_key": "sendDubKey"}


def target() -> str:
    return setting("phone_target") or "ar"


def order_for(source: str, item: dict[str, Any], mode: str, dialect: str) -> Any:
    from tarjim.server.jobs import Order

    return Order(source, target(), mode, dialect, item["name"], item.get("quality", ""))


def refused(order: Any) -> str:
    """What to tell the person when the order would fail later, e.g. no voice for the language."""
    from tarjim.server.job_routes import refusal

    reason = refusal(order)
    if not reason:
        return ""
    return say(REFUSED.get(reason, "actionFailed"), language=language(order.target).native)


def in_background(work: Callable[..., None], *args: Any) -> None:
    def run() -> None:
        try:
            work(*args)
        except Exception as error:
            note("answering a button", error)

    threading.Thread(target=run, daemon=True).start()


class Starting:
    follower: Follower
    uploads: Path
    waiting: Waiting

    def begin(self, bot: Bot, where: tuple[int, int], choice: tuple[str, str, str]) -> None:
        (chat, message), (mode, key, dialect) = where, choice
        item = self.waiting.take(key) if mode in MODES else None
        if item is None:
            return bot.edit(chat, message, say("phone_choice_expired"))
        problem = refused(order_for("", item, mode, dialect))
        if problem:
            return bot.edit(chat, message, problem)
        save("phone_mode", mode)
        try:
            source = self.fetched(bot, item, message)
        except (TelegramError, OSError):
            return bot.edit(chat, message, say("phone_fetch_failed"))
        task = self.follower.jobs.submit(order_for(source, item, mode, dialect))
        self.follower.adopt(bot, chat, message, task)
        return None

    def fetched(self, bot: Bot, item: dict[str, Any], status: int) -> str:
        if "file_id" not in item:
            return str(item["source"])
        bot.edit(item["chat"], status, say("stage_downloading"))
        folder = self.uploads / f"telegram-{secrets.token_hex(6)}"
        folder.mkdir(parents=True, exist_ok=True)

        def tell(done: int, total: int) -> None:
            bot.edit(item["chat"], status, shown(say("stage_downloading"), done, total))

        if item.get("message"):
            large.fetch(item["chat"], item["message"], folder / item["name"], tell)
        else:
            bot.fetch(item["file_id"], folder / item["name"], tell)
        return str(folder / item["name"])
