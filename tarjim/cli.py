import argparse
import sys
from pathlib import Path

from tarjim.fetch import resolve
from tarjim.job import Job
from tarjim.pipeline import run
from tarjim.translate.prompt import DIALECTS

DOWNLOADS = Path.home() / "Downloads" / "tarjim"


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="tarjim", description="Subtitles for any video")
    parser.add_argument("sources", nargs="+", help="video files or links")
    parser.add_argument("--to", default="ar", help="target language code, e.g. ar, en, fr, ja")
    parser.add_argument("--dialect", choices=sorted(DIALECTS), default="saudi",
                        help="Arabic style when --to ar")
    parser.add_argument("--no-burn", action="store_true", help="write .srt/.ass only")
    parser.add_argument("--font", default="", help="override the language's default font")
    parser.add_argument("--downloads", type=Path, default=DOWNLOADS,
                        help="where links are downloaded")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    args = parse(sys.argv[1:] if argv is None else argv)
    for source in args.sources:
        video = resolve(source, args.downloads)
        job = Job(video=video, target=args.to, dialect=args.dialect, burn=not args.no_burn,
                  font=args.font)
        cues, issues = run(job, report=lambda stage: print(f"  .. {stage}", flush=True))
        print(f"{video.name}: {len(cues)} subtitles, {len(issues)} issues")
        for issue in issues:
            print(f"  #{issue.number} {issue.kind}: {issue.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
