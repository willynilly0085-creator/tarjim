"""A tarjim server on a free port for the settings tests (2026-11-09), with its own home: the
saved settings go to a temporary TARJIM_HOME, never the person's ~/.tarjim."""
import http.client
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from tarjim.server.app import Handler
from tarjim.server.jobs import Board
from tarjim.server.pairing import Pairing
from tarjim.tools import Shelf

TOKEN = "p" * 32


@contextmanager
def serving(board: Board, uploads: Path) -> Iterator[int]:
    from http.server import ThreadingHTTPServer

    Handler.board, Handler.token, Handler.uploads = board, TOKEN, uploads
    Handler.shelf, Handler.pairing = Shelf(), Pairing()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()


def ask(port: int, request: str, data: Any = None) -> tuple[int, Any]:
    method, path = request.split(" ", 1)
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    body = json.dumps(data).encode() if data is not None else b""
    conn.request(method, path, body=body, headers={"X-Tarjim-Token": TOKEN,
                                                   "Content-Type": "application/json"})
    response = conn.getresponse()
    return response.status, json.loads(response.read() or b"{}")
