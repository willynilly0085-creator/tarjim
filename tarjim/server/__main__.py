import argparse
import json
import sys
from pathlib import Path

from tarjim.config import HOME, prepare_environment, private_home, save, setting, token
from tarjim.fetch import is_url, resolve
from tarjim.job import Job
from tarjim.server.app import PORT, serve
from tarjim.server.jobs import DUBBING, Board, Task

DOWNLOADS = Path.home() / "Downloads" / "tarjim"


def perform(task: Task, downloads: Path) -> None:
    order = task.order
    task.stage = "downloading" if is_url(order.source) else "hearing"
    task.video = resolve(order.source, HOME / "sources")
    downloads.mkdir(parents=True, exist_ok=True)
    job = Job(task.video, order.target, order.dialect, burn=order.mode != "srt",
              dub=DUBBING.get(order.mode, ""), out_dir=downloads)

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
    from tarjim.quiet import hide_child_windows

    hide_child_windows()
    attach_output()
    save("server_command", json.dumps([sys.executable, "-m", "tarjim.server"]))
    prepare_environment()


def run_alongside(port: int) -> Board:
    """The job board with what runs beside it: the phone bot and the watch for updates."""
    import threading

    from tarjim.memory import release_models
    from tarjim.phone.service import service
    from tarjim.server.update_routes import watch

    downloads = Path(setting("downloads") or DOWNLOADS)
    board = Board(lambda task: perform(task, downloads), idle=release_models)
    service.begin(board, HOME / "uploads")
    threading.Thread(target=watch, args=(board, port, threading.Event()), daemon=True).start()
    return board


def main(argv: list[str] | None = None) -> int:
    start_up()
    parser = argparse.ArgumentParser(prog="tarjim-serve", description="Local server for "
                                     "the tarjim browser extension")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--show-token", action="store_true")
    parser.add_argument("--gemini-key", default="", help="save your Gemini API key")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.gemini_key:
        save("gemini_api_key", args.gemini_key.strip())
        print("saved")
        return 0
    secret = token()
    if args.show_token:
        print(secret)
        return 0
    board = run_alongside(args.port)
    print(f"tarjim server on http://127.0.0.1:{args.port}", flush=True)
    serve(board, secret, HOME / "uploads", args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
