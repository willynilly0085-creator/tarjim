"""A small Telegram Bot API client. The bot's token is part of every address, so errors are
re-raised without the address and the token never reaches a log or a message."""
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from tarjim.phone.meter import Meter, Tell

API = "https://api.telegram.org"
TOKEN_SHAPE = re.compile(r"^\d{5,12}:[\w-]{30,50}$")
WAIT_SECONDS = 50
SEND_LIMIT = 50 * 1024 * 1024
FETCH_LIMIT = 20 * 1024 * 1024
UPLOAD_SECONDS = 600
SLOWEST_UPLOAD = 30_000
PARTIAL, WHOLE = 206, 200
FETCH_SECONDS = 900
SECRET = re.compile(r"\d{5,12}:[\w-]{30,50}")
PIECE = 64 * 1024
CONNECT_SECONDS = 10
STALL_SECONDS = 4
STALLS = 6
At = Callable[[int], None]


class TelegramError(RuntimeError):
    def __init__(self, reason: str, code: int = 0) -> None:
        super().__init__(reason)
        self.code = code


def well_formed(token: str) -> bool:
    return bool(TOKEN_SHAPE.match(token))


def note(where: str, error: Exception) -> None:
    """One line in the engine's log, never with the bot's token in it."""
    reason = SECRET.sub("<token>", str(error))[:200]
    print(f"phone bot, {where}: {type(error).__name__}: {reason}", flush=True)


def resume(address: str, out: BinaryIO, at: At | None = None) -> bool:
    """Append what the server sends from where the file stands; False when the line dropped or
    the server answered with something that cannot be appended."""
    import requests

    try:
        with requests.get(address, headers={"Range": f"bytes={out.tell()}-"}, stream=True,
                          timeout=(CONNECT_SECONDS, STALL_SECONDS)) as reply:
            if reply.status_code != PARTIAL and (out.tell() or reply.status_code != WHOLE):
                return False
            for piece in reply.iter_content(PIECE):
                out.write(piece)
                if at:
                    at(out.tell())
    except requests.RequestException:
        return False
    return True


def answer(reply: Any) -> Any:
    """What the Bot API answered, or a TelegramError carrying its own reason."""
    try:
        body = reply.json() if reply.headers.get("content-type", "").startswith(
            "application/json") else {}
    except ValueError:
        raise TelegramError(f"unreadable reply {reply.status_code}", reply.status_code) from None
    if not body.get("ok"):
        raise TelegramError(str(body.get("description", reply.status_code)),
                            int(body.get("error_code", reply.status_code)))
    return body["result"]


class Bot:
    def __init__(self, token: str) -> None:
        self.token = token

    def post(self, method: str, wait: float, **request: Any) -> Any:
        import requests

        try:
            reply = requests.post(f"{API}/bot{self.token}/{method}", timeout=wait, **request)
        except requests.RequestException as error:
            raise TelegramError(type(error).__name__) from None
        return answer(reply)

    def call(self, method: str, wait: float = 30, **params: Any) -> Any:
        return self.post(method, wait, data=params)

    def me(self) -> dict[str, Any]:
        return dict(self.call("getMe"))

    def updates(self, offset: int) -> list[dict[str, Any]]:
        return list(self.call("getUpdates", wait=WAIT_SECONDS + 10, offset=offset,
                              timeout=WAIT_SECONDS) or [])

    def say(self, chat: int, text: str, **extra: Any) -> int:
        return int(self.call("sendMessage", chat_id=chat, text=text, **extra)["message_id"])

    def edit(self, chat: int, message: int, text: str, **extra: Any) -> None:
        try:
            self.call("editMessageText", chat_id=chat, message_id=message, text=text, **extra)
        except TelegramError as error:
            if "not modified" not in str(error):
                raise

    def send_file(self, chat: int, path: Path, video: bool, tell: Tell | None = None) -> None:
        """Send the file as it is read from disk, telling how far it is."""
        from tarjim.phone.upload import Body

        method, field = ("sendVideo", "video") if video else ("sendDocument", "document")
        body = Body({"chat_id": str(chat), "supports_streaming": "true" if video else "false"},
                    field, path)
        body.watch = Meter(tell) if tell else None
        try:
            self.post(method, max(UPLOAD_SECONDS, path.stat().st_size / SLOWEST_UPLOAD),
                      data=body, headers={"Content-Type": body.content_type})
        finally:
            body.close()

    def fetch(self, file_id: str, target: Path, tell: Tell | None = None) -> None:
        """Telegram's file server often stalls partway, so each try continues the file; only
        tries in a row that bring nothing count against it, within a quarter of an hour."""
        info = self.call("getFile", file_id=file_id)
        address, size = f"{API}/file/bot{self.token}/{info['file_path']}", int(
            info.get("file_size") or 0)
        meter = Meter(tell) if tell else None
        at: At | None = (lambda done: meter(done, size)) if meter else None
        stalls, deadline = 0, time.monotonic() + FETCH_SECONDS
        with target.open("wb") as out:
            while stalls < STALLS and time.monotonic() < deadline:
                before = out.tell()
                if resume(address, out, at) or 0 < size <= out.tell():
                    return
                stalls = 0 if out.tell() > before else stalls + 1
        target.unlink(missing_ok=True)
        raise TelegramError("download stalled")
