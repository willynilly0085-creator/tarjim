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
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from tarjim import config
from tarjim.config import setting
from tarjim.phone.meter import Meter, Tell
from tarjim.phone.telegram import TelegramError

LIMIT = 2000 * 1024 * 1024
SESSION = "telegram_session"
APP_ID = re.compile(r"^\d{4,12}$")
APP_HASH = re.compile(r"^[0-9a-f]{32}$")
ONE_AT_A_TIME = threading.Lock()
Work = Callable[[Any], Awaitable[Any]]


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
