"""The engine's port, taken by one engine only.

Python's HTTP server asks for SO_REUSEADDR, and on Windows that lets a second process listen on a
port another is already listening on. Two engines then split the job list, run two jobs at once
(the memory lock is per process) and fight over the phone bot. On Windows the port is taken with
SO_EXCLUSIVEADDRUSE instead; elsewhere SO_REUSEADDR never shares a listening port. The port is
taken before anything else starts, so a second engine leaves at once with a clear line in the log.

An engine that replaces another (a restart onto new code, renew.py) is not a second engine: it
keeps asking. Twice (2026-11-14, 2026-11-15) such an engine was refused the port within a second
of its start and closed, and no engine was left: the phone bot went quiet and the extension found
nothing until someone started tarjim by hand. Why the port was still held is not known: two
restarts watched every 30 ms handed it over cleanly, and four small copies of the handover never
refused. So the lines it prints say what it saw, for the next time.
"""
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATIENCE = 30.0  # the engine being replaced ends itself 1.5 s after it started this one
AGAIN = 0.25


class OnlyListener(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"
    # The page loads its 40-odd scripts at once (2026-11-09): with the default queue of 5,
    # Windows refused some of them and the page stopped half drawn.
    request_queue_size = 64

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Taken(RuntimeError):
    """Another program, most likely a tarjim engine already running, holds the port."""


def noted(port: int, before: int, refused: int) -> int:
    if not refused:
        from tarjim.installer import alive

        state = "still running" if alive(before) else "gone"
        print(f"port {port} is held though this engine replaces engine {before}, which is "
              f"{state}: asking again for up to {PATIENCE:.0f} s", flush=True)
    return refused + 1


def take_port(port: int, handler: type[BaseHTTPRequestHandler], before: int = 0) -> OnlyListener:
    """`before`: the engine this one replaces, which makes it keep asking for PATIENCE."""
    began, refused = time.monotonic(), 0
    while True:
        try:
            listener = OnlyListener(("127.0.0.1", port), handler)
        except OSError as error:
            if not before or time.monotonic() - began >= PATIENCE:
                raise Taken(f"port {port} is in use, most likely by a tarjim engine already "
                            "running; this one closes") from error
            refused = noted(port, before, refused)
            time.sleep(AGAIN)
            continue
        if refused:
            print(f"port {port} was let go {time.monotonic() - began:.1f} s later, after "
                  f"{refused} refusal(s)", flush=True)
        return listener
