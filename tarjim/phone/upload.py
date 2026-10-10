"""A file sent to the Bot API as it is read from disk, so the upload's progress can be told. The
usual way builds the whole request in memory first and says nothing until it is over."""
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

PIECE = 256 * 1024
Watch = Callable[[int, int], None]


class Body:
    """A multipart form with one file, read piece by piece. It knows its length, so the request
    is sent with a Content-Length, which the Bot API needs."""

    def __init__(self, fields: dict[str, str], field: str, path: Path) -> None:
        self.boundary = f"tarjim{secrets.token_hex(12)}"
        named = path.name.replace('"', "%22").replace("\r", "").replace("\n", "")
        text = "".join(f'--{self.boundary}\r\nContent-Disposition: form-data; name="{key}"'
                       f"\r\n\r\n{value}\r\n" for key, value in fields.items())
        text += (f'--{self.boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                 f'filename="{named}"\r\nContent-Type: application/octet-stream\r\n\r\n')
        self.head, self.tail = text.encode("utf-8"), f"\r\n--{self.boundary}--\r\n".encode()
        self.size, self.sent = path.stat().st_size, 0
        self.length = len(self.head) + self.size + len(self.tail)
        self.file: BinaryIO = path.open("rb")
        self.watch: Watch | None = None

    def __len__(self) -> int:
        return self.length

    @property
    def content_type(self) -> str:
        return f"multipart/form-data; boundary={self.boundary}"

    def read(self, _size: int = -1) -> bytes:
        if self.head:
            first, self.head = self.head, b""
            return first
        piece = self.file.read(PIECE)
        if piece:
            self.sent += len(piece)
            if self.watch:
                self.watch(self.sent, self.size)
            return piece
        last, self.tail = self.tail, b""
        return last

    def close(self) -> None:
        self.file.close()
