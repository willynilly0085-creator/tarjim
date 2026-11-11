import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from tarjim import same_code
from tarjim.config import HOME, prepare_environment, private_home, save, token
from tarjim.fetch import is_url, resolve
from tarjim.installer import module_command, wait_for_exit
from tarjim.job import CHECKPOINT, PROGRESS, Job
from tarjim.prefs.model import Prefs
from tarjim.server.app import PORT, Handler, serve
from tarjim.server.housekeeping import Undo
from tarjim.server.jobs import DUBBING, Board, Order, Task
from tarjim.server.listener import Taken, take_port

DOWNLOADS = Path.home() / "Downloads" / "tarjim"


def undo_for(job: Job) -> list[Undo]:
    """A cancel takes back the job's results and its work folder, as far as this run made
    them; inside the folder first, then the folder itself when this run created it."""
    stem, results, work = job.video.stem, job.output(""), HOME / "cache"
    return [Undo(results.parent, lambda name: name.startswith(results.name)),
            Undo(work / stem), Undo(work, lambda name: name == stem)]


def settings_for(order: Order) -> Prefs:
    """The settings the order was made with; an order kept before 2026-11-09 has none, and
    runs with what is saved now."""
    from tarjim.prefs.job import from_snapshot
    from tarjim.prefs.store import current, note

    if not order.prefs:
        return current(order.target, order.tweaks)
    prefs = from_snapshot(order.prefs, order.target)
    for line in prefs.notes:  # a folder gone since, a rule a newer release made stricter
        note(line)
    return prefs


def folder_for(prefs: Prefs, downloads: Path) -> Path:
    """Where the files go: the person's folder, or the usual one when they kept it, or when
    theirs is gone (a drive taken out), which the settings' check already noted."""
    from tarjim.prefs.table import SPECS

    chosen = prefs.output.folder
    if chosen == SPECS["output.folder"].default or not Path(chosen).is_dir():
        return downloads
    return Path(chosen)


def job_for(task: Task, video: Path, downloads: Path) -> Job:
    order = task.order
    prefs = settings_for(order)
    dub = DUBBING.get(order.mode, "")
    folder = folder_for(prefs, downloads)
    folder.mkdir(parents=True, exist_ok=True)
    # a dub carries written subtitles unless the person wants the clean voice (2026-11-09)
    burn = order.mode != "srt" and (not dub or prefs.output.burn_with_dub)
    return Job(video, order.target, order.dialect, burn=burn, dub=dub, out_dir=folder,
               cache_dir=HOME / "cache", relisten=order.relisten, prefs=prefs)


def perform(task: Task, downloads: Path) -> None:
    order = task.order
    CHECKPOINT.set(task.checkpoint)
    PROGRESS.set(lambda done, total: setattr(task, "moved", (done, total)))
    task.stage = "downloading" if is_url(order.source) else "hearing"
    task.undo.append(Undo(HOME / "sources", keep=lambda: task.video))
    task.video = resolve(order.source, HOME / "sources", order.quality)
    task.checkpoint()
    task.moved = (0, 0)
    job = job_for(task, task.video, downloads)
    task.undo.extend(undo_for(job))

    def report(stage: str) -> None:
        task.stage = stage
        task.checkpoint()

    make(task, job, report)


def make(task: Task, job: Job, report: Callable[[str], None]) -> None:
    """The files, and what the job knows is not right in them: until 2026-11-08 the checks run()
    returned, the speech left without words and the timing check were dropped here, and the page
    showed plain success."""
    from tarjim.findings import collecting
    from tarjim.pipeline import run

    found = collecting()
    cues, issues = run(job, report)
    task.notes = found.notes(cues, issues)
    from tarjim.post import SUFFIX

    candidates = [job.output(".dub.mp4"), job.output(".mp4"), job.output(".srt"),
                  job.output(SUFFIX)]
    task.outputs = [p for p in candidates if p.exists()]


def attach_output() -> None:
    private_home()
    if sys.stdout is None:
        log = (HOME / "server.log").open("a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]


def start_up() -> None:
    from tarjim import autostart, native_setup
    from tarjim.quiet import hide_child_windows

    hide_child_windows()
    attach_output()
    autostart.refresh()
    native_setup.register()  # the browser's way to start this engine, for a moved folder too
    save("server_command", json.dumps(module_command("tarjim.server")))
    prepare_environment()


def run_alongside(port: int) -> Board:
    """The job board with what runs beside it: the phone bot, the watch for updates, and the
    replacement of chat entries older versions wrote."""
    import threading

    from tarjim.memory import release_models
    from tarjim.phone.service import service
    from tarjim.server.housekeeping import sweep
    from tarjim.server.job_record import keep
    from tarjim.server.link_upgrade import refresh
    from tarjim.server.update_routes import watch

    # the person's own folder comes with each order since 2026-11-09 (prefs output.folder)
    board = Board(lambda task: perform(task, DOWNLOADS), idle=release_models)
    keep(board)
    sweep([HOME / "uploads", HOME / "sources", HOME / "cache"])
    service.begin(board, HOME / "uploads")
    threading.Thread(target=watch, args=(board, port, threading.Event()), daemon=True).start()
    threading.Thread(target=refresh, daemon=True).start()
    return board


def options(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="tarjim-serve", description="Local server for "
                                     "the tarjim browser extension")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--show-token", action="store_true")
    parser.add_argument("--gemini-key", default="", help="save your Gemini API key")
    parser.add_argument("--after", type=int, default=0, help=argparse.SUPPRESS)
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def main(argv: list[str] | None = None) -> int:
    same_code.hold()  # first: every module imported later comes from the code read now
    start_up()
    args = options(argv)
    if args.gemini_key:
        save("gemini_api_key", args.gemini_key.strip())
        print("saved")
        return 0
    secret = token()
    if args.show_token:
        print(secret)
        return 0
    wait_for_exit(args.after)  # the engine this one replaces lets go of the port
    try:
        listener = take_port(args.port, Handler)  # first: a second engine starts nothing
    except Taken as busy:
        print(busy, flush=True)
        return 1
    board = run_alongside(args.port)
    print(f"tarjim server on http://127.0.0.1:{args.port}", flush=True)
    serve(listener, board, secret, HOME / "uploads")
    return 0

