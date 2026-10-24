import argparse
import json
import sys
from pathlib import Path

from tarjim import same_code
from tarjim.config import HOME, prepare_environment, private_home, save, setting, token
from tarjim.fetch import is_url, resolve
from tarjim.installer import module_command, wait_for_exit
from tarjim.job import CHECKPOINT, PROGRESS, Job
from tarjim.server.app import PORT, serve
from tarjim.server.housekeeping import Undo
from tarjim.server.jobs import DUBBING, Board, Task

DOWNLOADS = Path.home() / "Downloads" / "tarjim"


def undo_for(job: Job) -> list[Undo]:
    """A cancel takes back the job's results and its work folder, as far as this run made
    them; inside the folder first, then the folder itself when this run created it."""
    stem, results, work = job.video.stem, job.output(""), HOME / "cache"
    return [Undo(results.parent, lambda name: name.startswith(results.name)),
            Undo(work / stem), Undo(work, lambda name: name == stem)]


def perform(task: Task, downloads: Path) -> None:
    order = task.order
    CHECKPOINT.set(task.checkpoint)
    PROGRESS.set(lambda done, total: setattr(task, "moved", (done, total)))
    task.stage = "downloading" if is_url(order.source) else "hearing"
    task.undo.append(Undo(HOME / "sources", keep=lambda: task.video))
    task.video = resolve(order.source, HOME / "sources")
    task.checkpoint()
    task.moved = (0, 0)
    downloads.mkdir(parents=True, exist_ok=True)
    job = Job(task.video, order.target, order.dialect, burn=order.mode != "srt",
              dub=DUBBING.get(order.mode, ""), out_dir=downloads, cache_dir=HOME / "cache")
    task.undo.extend(undo_for(job))

    def report(stage: str) -> None:
        task.stage = stage
        task.checkpoint()

    from tarjim.pipeline import run

    run(job, report)
    candidates = [job.output(".dub.mp4"), job.output(".mp4"), job.output(".srt")]
    task.outputs = [p for p in candidates if p.exists()]


def attach_output() -> None:
    private_home()
    if sys.stdout is None:
        log = (HOME / "server.log").open("a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def start_up() -> None:
    from tarjim import autostart
    from tarjim.quiet import hide_child_windows

    hide_child_windows()
    attach_output()
    autostart.refresh()
    save("server_command", json.dumps(module_command("tarjim.server")))
    prepare_environment()


def run_alongside(port: int) -> Board:
    """The job board with what runs beside it: the phone bot, the watch for updates, and the
    replacement of chat entries older versions wrote."""
    import threading

    from tarjim.memory import release_models
    from tarjim.phone.service import service
    from tarjim.server.housekeeping import sweep
    from tarjim.server.link_upgrade import refresh
    from tarjim.server.renew import restore
    from tarjim.server.update_routes import watch

    downloads = Path(setting("downloads") or DOWNLOADS)
    board = Board(lambda task: perform(task, downloads), idle=release_models)
    restore(board)
    sweep([HOME / "uploads", HOME / "sources", HOME / "cache"])
    service.begin(board, HOME / "uploads")
    threading.Thread(target=watch, args=(board, port, threading.Event()), daemon=True).start()
    threading.Thread(target=refresh, daemon=True).start()
    return board


def main(argv: list[str] | None = None) -> int:
    same_code.hold()  # first: every module imported later comes from the code read now
    start_up()
    parser = argparse.ArgumentParser(prog="tarjim-serve", description="Local server for "
                                     "the tarjim browser extension")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--show-token", action="store_true")
    parser.add_argument("--gemini-key", default="", help="save your Gemini API key")
    parser.add_argument("--after", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.gemini_key:
        save("gemini_api_key", args.gemini_key.strip())
        print("saved")
        return 0
    secret = token()
    if args.show_token:
        print(secret)
        return 0
    wait_for_exit(args.after)  # the engine this one replaces lets go of the port
    board = run_alongside(args.port)
    print(f"tarjim server on http://127.0.0.1:{args.port}", flush=True)
    serve(board, secret, HOME / "uploads", args.port)
    return 0

