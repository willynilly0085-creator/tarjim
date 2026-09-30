"""A small Telegram Bot API client. The bot's token is part of every address, so errors are
re-raised without the address and the token never reaches a log or a message."""
import re
from pathlib import Path
from typing import Any

API = "https://api.telegram.org"
TOKEN_SHAPE = re.compile(r"^\d{5,12}:[\w-]{30,50}$")
WAIT_SECONDS = 50
SEND_LIMIT = 50 * 1024 * 1024
FETCH_LIMIT = 20 * 1024 * 1024


class TelegramError(RuntimeError):
    def __init__(self, reason: str, code: int = 0) -> None:
        super().__init__(reason)
        self.code = code


def well_formed(token: str) -> bool:
    return bool(TOKEN_SHAPE.match(token))


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
        with path.open("rb") as handle:
            self.call(method, files={field: (path.name, handle)}, wait=600, chat_id=chat,
                      supports_streaming="true" if video else "false")

    def fetch(self, file_id: str, target: Path) -> None:
        import requests

        info = self.call("getFile", file_id=file_id)
        try:
            reply = requests.get(f"{API}/file/bot{self.token}/{info['file_path']}", timeout=300)
            reply.raise_for_status()
        except requests.RequestException as error:
            raise TelegramError(type(error).__name__) from None
        target.write_bytes(reply.content)
