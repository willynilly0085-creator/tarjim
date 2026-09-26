import argparse
import sys
from pathlib import Path

from tarjim.pipeline import Job, run
from tarjim.translate.prompt import DIALECTS


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="tarjim", description="Arabic subtitles for any video")
    parser.add_argument("videos", nargs="+", type=Path)
    parser.add_argument("--dialect", choices=sorted(DIALECTS), default="saudi")
    parser.add_argument("--no-burn", action="store_true", help="write .ass/.srt only")
    parser.add_argument("--font", default="Dubai")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    args = parse(sys.argv[1:] if argv is None else argv)
    for video in args.videos:
        job = Job(video=video, dialect=args.dialect, burn=not args.no_burn, font=args.font)
        cues, issues = run(job)
        print(f"{video.name}: {len(cues)} subtitles, {len(issues)} issues")
        for issue in issues:
            print(f"  #{issue.number} {issue.kind}: {issue.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
