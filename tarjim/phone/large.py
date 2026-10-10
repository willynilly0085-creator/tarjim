"""Videos larger than Telegram lets a bot handle: up to 2 GB in, and the result back whole.

Through the Bot API a bot may download 20 MB and upload 50 MB. A bot that talks to Telegram the
way an app does (MTProto, through Telethon) is not held to that. Telegram asks every app for an
id and a hash, which the person creates once at my.telegram.org and saves on tarjim's page. It is
still the same bot: it signs in with the same token. One transfer runs at a time, each on its own
connection. The sign-in Telegram hands back is a secret like the hash, so it is kept in the
system's vault with the keys, never in a session file on disk.
"""
import asyncio
import re
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from tarjim import config
from tarjim.config import setting
from tarjim.phone.telegram import TelegramError

LIMIT = 2000 * 1024 * 1024
SESSION = "telegram_session"
APP_ID = re.compile(r"^\d{4,12}$")
APP_HASH = re.compile(r"^[0-9a-f]{32}$")
ONE_AT_A_TIME = threading.Lock()
Work = Callable[[Any], Awaitable[Any]]
Tell = Callable[[int, int], None]
EVERY = 4.0
MB = 1024 * 1024


def bar(done: int, total: int, cells: int = 10) -> str:
    """A bar of filled and empty cells: Telegram has no progress bar for a bot's message, so the
    message draws its own."""
    filled = min(cells, round(cells * done / max(total, 1)))
    return "▰" * filled + "▱" * (cells - filled)


def shown(step: str, done: int, total: int) -> str:
    """The step's name, and under it the bar with the megabytes so far."""
    from tarjim.phone.words import say

    return "\n".join((step, f"{bar(done, total)} " + say("phone_progress", done=done, total=total)))


class Meter:
    """Say how far a transfer is, in megabytes, at most once every few seconds. A message that
    cannot be shown never stops the transfer."""

    def __init__(self, tell: Tell) -> None:
        self.tell, self.last = tell, 0.0

    def __call__(self, done: int, total: int) -> None:
        if time.monotonic() - self.last < EVERY:
            return
        self.last = time.monotonic()
        try:
            self.tell(round(done / MB), max(1, round(total / MB)))
        except (TelegramError, OSError):
            return


def well_formed(app_id: str, app_hash: str) -> bool:
    return bool(APP_ID.match(app_id) and APP_HASH.match(app_hash))


def ready() -> bool:
    return bool(setting("telegram_token")) and well_formed(
        setting("telegram_api_id"), setting("telegram_api_hash"))


async def connected(work: Work) -> Any:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    kept = setting(SESSION)
    client = TelegramClient(StringSession(kept), int(setting("telegram_api_id")),
                            setting("telegram_api_hash"))
    try:
        await client.start(bot_token=setting("telegram_token"))
        if client.session.save() != kept:
            config.save(SESSION, client.session.save())
        return await work(client)
    finally:
        await client.disconnect()


def run(work: Work) -> Any:
    """Do one thing as the bot over the app protocol; any failure is a TelegramError whose words
    never include the token or the hash."""
    with ONE_AT_A_TIME:
        try:
            return asyncio.run(connected(work))
        except TelegramError:
            raise
        except Exception as error:
            raise TelegramError(f"large files: {type(error).__name__}") from None


def fetch(chat: int, message: int, target: Path, tell: Tell | None = None) -> None:
    async def work(client: Any) -> None:
        found = await client.get_messages(chat, ids=message)
        meter = Meter(tell) if tell else None
        if found is None or not await client.download_media(
                found, file=str(target), progress_callback=meter):
            raise TelegramError("large files: the video is no longer in the chat")

    run(work)


def send(chat: int, path: Path, tell: Tell | None = None) -> None:
    async def work(client: Any) -> None:
        video = path.suffix == ".mp4"
        await client.send_file(chat, str(path), supports_streaming=video,
                               force_document=not video,
                               progress_callback=Meter(tell) if tell else None)

    run(work)


def works() -> bool:
    """Whether Telegram accepts the saved id and hash for this bot."""
    async def work(client: Any) -> Any:
        return await client.get_me()

    try:
        return run(work) is not None
    except TelegramError:
        return False


def forget() -> None:
    for name in ("telegram_api_id", "telegram_api_hash", SESSION):
        config.save(name, "")
