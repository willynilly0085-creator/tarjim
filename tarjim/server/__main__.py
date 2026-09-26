import argparse
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
    task.video = resolve(order.source, downloads)
    job = Job(task.video, order.target, order.dialect, burn=order.mode != "srt",
              dub=DUBBING.get(order.mode, ""))

    def report(stage: str) -> None:
        task.stage = stage

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


def main(argv: list[str] | None = None) -> int:
    attach_output()
    prepare_environment()
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
    downloads = Path(setting("downloads") or DOWNLOADS)
    board = Board(lambda task: perform(task, downloads))
    print(f"tarjim server on http://127.0.0.1:{args.port}", flush=True)
    serve(board, secret, HOME / "uploads", args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
