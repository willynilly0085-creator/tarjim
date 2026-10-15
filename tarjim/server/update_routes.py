"""Updates from the page and by themselves: what version this is, whether a newer one is out, and
the background watch that, with automatic updates on and nothing running, installs it, brings
the libraries onto the versions tested with this release, and keeps yt-dlp current."""
import os
import threading
from typing import Any, ClassVar

from tarjim import downloader, update
from tarjim.server.jobs import Board

Query = dict[str, list[str]]
FIRST_LOOK = 60.0
LOOK_EVERY = 3600.0
CLOSE_AFTER = 1.5


def idle(board: Board) -> bool:
    return all(task.finished for task in board.recent())


def close_soon(started: bool) -> bool:
    """The installer started waits for this engine to close before it replaces it."""
    if started:
        threading.Timer(CLOSE_AFTER, os._exit, (0,)).start()
    return started


def replace_engine(port: int) -> bool:
    """Start the installer for the latest release, then close this engine so it can be replaced."""
    return close_soon(update.start(update.latest(), port))


def look(board: Board, port: int) -> None:
    if not idle(board):
        return
    state = update.view()
    if state["available"] and state["automatic"] and state["can_install"]:
        replace_engine(port)
    elif update.repair_due():
        close_soon(update.repair(port))
    else:
        downloader.refresh(idle=True)


def settle_after_update() -> None:
    """A fresh install replaced the engine's folder: bring back what lives outside or beside it."""
    from tarjim.dub.voice_setup import repair
    from tarjim.extension_home import extension_folder

    extension_folder()
    repair()


def watch(board: Board, port: int, stop: threading.Event) -> None:
    settle_after_update()
    wait = FIRST_LOOK
    while not stop.wait(wait):
        wait = LOOK_EVERY
        try:
            look(board, port)
        except Exception as error:
            print(f"update watch: {type(error).__name__}: {error}", flush=True)


class UpdateRoutes:
    board: ClassVar[Board]
    server: Any

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def update_state(self, _query: Query) -> None:
        self.reply(200, update.view())

    def update_apply(self, _query: Query) -> None:
        state = update.view()
        if not state["available"] or not state["can_install"]:
            return self.reply(409, {"error": "update"})
        if not idle(self.board):
            return self.reply(409, {"error": "busy"})
        started = replace_engine(int(self.server.server_address[1]))
        self.reply(200 if started else 409, {"started": started})
