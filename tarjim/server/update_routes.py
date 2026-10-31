"""Updates from the page and by themselves: what version this is, whether a newer one is out, and
the background watch that, with automatic updates on and nothing running, installs it, brings
the libraries onto the versions tested with this release, and keeps yt-dlp, tarjim's own Node.js
and ffmpeg, and the Python under its environment current; and, once a minute, restarts the engine
into its own code when that changed on disk (renew.py) and moves local listening onto its newer
models (listen_upgrade.py)."""
import os
import threading
from typing import Any, ClassVar

from tarjim import downloader, ffmpeg_update, node_update, python_update, same_code, update
from tarjim.server.jobs import Board
from tarjim.server.renew import Renewal

Query = dict[str, list[str]]
TICK = 60.0
LOOK_EVERY = 60  # ticks: an hour, the first a minute after the start
CLOSE_AFTER = 1.5


def idle(board: Board) -> bool:
    """No job running and no tool downloading: a restart would cut a model download short."""
    from tarjim.tools import shelf

    downloading = any(p.state == "downloading" for p in shelf().progress.values())
    return not downloading and all(task.finished for task in board.recent())


def close_soon(started: bool, board: Board | None = None) -> bool:
    """The installer started waits for this engine to close before it replaces it. A job asked
    for in the meantime is written down for the next engine instead of being lost."""
    if started:
        if board is not None:
            board.closing = True
            board.saved()
        threading.Timer(CLOSE_AFTER, os._exit, (0,)).start()
    return started


def replace_engine(port: int, board: Board) -> bool:
    """Start the installer for the latest release, then close this engine so it can be replaced."""
    return close_soon(update.start(update.latest(), port), board)


def look(board: Board, port: int) -> None:
    if not idle(board):
        return
    state = update.view()
    if state["available"] and state["automatic"] and state["can_install"]:
        replace_engine(port, board)
    elif update.repair_due():
        close_soon(update.repair(port), board)
    else:
        keep_current(board, port)


def keep_current(board: Board, port: int) -> None:
    """What tarjim brought along; the Python last, because its rebuild closes the engine."""
    downloader.refresh(idle=True)
    node_update.refresh(idle=idle(board))
    ffmpeg_update.refresh(idle=idle(board))
    close_soon(python_update.refresh(idle(board), port), board)


def settle_after_update() -> None:
    """A fresh install replaced the engine's folder: bring back what lives outside or beside it."""
    from tarjim.dub.voice_setup import repair
    from tarjim.extension_home import extension_folder

    extension_folder()
    repair()
    from tarjim.old_environment import forget_old_environment

    forget_old_environment()


def upgrade_listening(board: Board) -> None:
    from tarjim.listen_upgrade import step
    from tarjim.tools import shelf

    done = step(shelf(), idle(board))
    if done in ("started", "removed earlier"):
        print(f"listening models: {done}", flush=True)


def tick(board: Board, port: int, renewal: Renewal, count: int) -> None:
    if idle(board) and renewal.due() and idle(board):
        close_soon(renewal.restart(board), board)
        return
    if count % LOOK_EVERY == 0:
        look(board, port)
    upgrade_listening(board)


def watch(board: Board, port: int, stop: threading.Event) -> None:
    settle_after_update()
    renewal, count = Renewal(next(iter(same_code.KEPT), None)), 0
    while not stop.wait(TICK):
        try:
            tick(board, port, renewal, count)
        except Exception as error:
            print(f"update watch: {type(error).__name__}: {error}", flush=True)
        count += 1


class UpdateRoutes:
    board: ClassVar[Board]
    server: Any

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def update_state(self, _query: Query) -> None:
        from tarjim.extension_home import extension_folder

        # The extension reloads when this reports a newer version, so the folder it loads from
        # is brought up to date first: tarjim's files can change while the engine runs.
        extension_folder()
        self.reply(200, update.view())

    def update_apply(self, _query: Query) -> None:
        state = update.view()
        if not state["available"] or not state["can_install"]:
            return self.reply(409, {"error": "update"})
        if not idle(self.board):
            return self.reply(409, {"error": "busy"})
        started = replace_engine(int(self.server.server_address[1]), self.board)
        self.reply(200 if started else 409, {"started": started})
