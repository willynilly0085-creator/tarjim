"""A small Telegram Bot API client. The bot's token is part of every address, so errors are
re-raised without the address and the token never reaches a log or a message."""
import re
from pathlib import Path
from typing import Any, BinaryIO

API = "https://api.telegram.org"
TOKEN_SHAPE = re.compile(r"^\d{5,12}:[\w-]{30,50}$")
WAIT_SECONDS = 50
SEND_LIMIT = 50 * 1024 * 1024
FETCH_LIMIT = 20 * 1024 * 1024
UPLOAD_SECONDS = 600
SLOWEST_UPLOAD = 30_000
PARTIAL = 206
PIECE = 64 * 1024
CONNECT_SECONDS = 10
STALL_SECONDS = 4
STALLS = 6


class TelegramError(RuntimeError):
    def __init__(self, reason: str, code: int = 0) -> None:
        super().__init__(reason)
        self.code = code


def well_formed(token: str) -> bool:
    return bool(TOKEN_SHAPE.match(token))


def resume(address: str, out: BinaryIO) -> bool:
    """Append what the server sends from where the file stands; False when the line dropped."""
    import requests

    try:
        with requests.get(address, headers={"Range": f"bytes={out.tell()}-"}, stream=True,
                          timeout=(CONNECT_SECONDS, STALL_SECONDS)) as reply:
            if reply.status_code != PARTIAL:
                raise TelegramError(str(reply.status_code), reply.status_code)
            for piece in reply.iter_content(PIECE):
                out.write(piece)
    except requests.RequestException:
        return False
    return True


class Bot:
    def __init__(self, token: str) -> None:
        self.token = token

    def call(self, method: str, files: dict[str, Any] | None = None, wait: float = 30,
             **params: Any) -> Any:
        import requests

        try:
            reply = requests.post(f"{API}/bot{self.token}/{method}", data=params, files=files,
                                  timeout=wait)
        except requests.RequestException as error:
            raise TelegramError(type(error).__name__) from None
        body = reply.json() if reply.headers.get("content-type", "").startswith(
            "application/json") else {}
        if not body.get("ok"):
            raise TelegramError(str(body.get("description", reply.status_code)),
                                int(body.get("error_code", reply.status_code)))
        return body["result"]

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

    def send_file(self, chat: int, path: Path, video: bool) -> None:
        method, field = ("sendVideo", "video") if video else ("sendDocument", "document")
        wait = max(UPLOAD_SECONDS, path.stat().st_size / SLOWEST_UPLOAD)
        with path.open("rb") as handle:
            self.call(method, files={field: (path.name, handle)}, wait=wait, chat_id=chat,
                      supports_streaming="true" if video else "false")

    def fetch(self, file_id: str, target: Path) -> None:
        """Telegram's file server often stalls partway, so each try continues the file; only
        tries in a row that bring nothing count against it."""
        info = self.call("getFile", file_id=file_id)
        address, stalls = f"{API}/file/bot{self.token}/{info['file_path']}", 0
        with target.open("wb") as out:
            while stalls < STALLS:
                before = out.tell()
                if resume(address, out):
                    return
                stalls = 0 if out.tell() > before else stalls + 1
        target.unlink(missing_ok=True)
        raise TelegramError("download stalled")
