"""What the browser runs when tarjim's extension finds the engine stopped: start it, then answer.

Chrome and Edge start this program (native messaging, registered by native_setup.py) only for the
extensions its manifest lists, and talk to it over its standard input and output: each message is
four bytes of length, then JSON. It reads one message, starts the engine the way the tarjim
shortcut does (wake.py: outside the browser's own process group, so it keeps running), answers,
and ends. It never reads or changes anything else.
"""
import json
import struct
import sys
from typing import Any, BinaryIO

LENGTH = struct.Struct("<I")
MOST = 4096  # the extension sends a few bytes; anything longer is not tarjim's


def read_message(stream: BinaryIO) -> dict[str, Any]:
    head = stream.read(LENGTH.size)
    if len(head) < LENGTH.size:
        return {}
    size = LENGTH.unpack(head)[0]
    if size > MOST:
        return {}
    try:
        message = json.loads(stream.read(size) or b"{}")
    except ValueError:
        return {}
    return message if isinstance(message, dict) else {}


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    stream.write(LENGTH.pack(len(body)) + body)
    stream.flush()


def answer(message: dict[str, Any]) -> dict[str, Any]:
    from tarjim.assistant_http import SERVER
    from tarjim.config import setting
    from tarjim.wake import answers, start

    if not message.get("wake"):
        return {"error": "unknown"}
    if answers(setting("server") or SERVER):
        return {"running": True}
    return {"started": start()}


def main() -> int:
    write_message(sys.stdout.buffer, answer(read_message(sys.stdin.buffer)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
