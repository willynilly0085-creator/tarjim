"""The engine's port, taken by one engine only.

Python's HTTP server asks for SO_REUSEADDR, and on Windows that lets a second process listen on a
port another is already listening on. Two engines then split the job list, run two jobs at once
(the memory lock is per process) and fight over the phone bot. On Windows the port is taken with
SO_EXCLUSIVEADDRUSE instead; elsewhere SO_REUSEADDR never shares a listening port. The port is
taken before anything else starts, so a second engine leaves at once with a clear line in the log.
"""
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class OnlyListener(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Taken(RuntimeError):
    """Another program, most likely a tarjim engine already running, holds the port."""


def take_port(port: int, handler: type[BaseHTTPRequestHandler]) -> OnlyListener:
    try:
        return OnlyListener(("127.0.0.1", port), handler)
    except OSError as error:
        raise Taken(f"port {port} is in use, most likely by a tarjim engine already "
                    "running; this one closes") from error
