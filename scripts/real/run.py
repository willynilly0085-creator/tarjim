"""tarjim itself on each clip of the real-speech bench: the chosen listener over the network,
the listener and the aligner of this computer, the cue builder and the translator, exactly as a
job runs them (pipeline.run), in a home of its own with a new user's settings. Nothing is
faked and nothing is burned (a clip is sound only).

Each clip's folder under runs/<label>/ keeps what the job made (result.json: its lines with
their words and translations, its doubts, its notes, the seconds each stage took), its log and
its kept work. A clip already run under the label is not run again.

    python run.py [--label L] [--hearing OTHER] [clip ...]      default: every clip built

--hearing OTHER starts each clip from what the listener wrote in the run labelled OTHER (its
passes, without what that run filled in afterwards), so two versions of tarjim's code are
compared on the same hearing: a listener never writes the same thing twice.
"""
import argparse
import contextlib
import json
import sys
import time
import traceback
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path
from typing import Any

from paths import CLIPS, RUNS, prepare

prepare()

from tarjim import pipeline  # noqa: E402
from tarjim.findings import collecting  # noqa: E402
from tarjim.job import Job  # noqa: E402
from tarjim.models import Cue  # noqa: E402

Row = dict[str, Any]


def line(cue: Cue) -> Row:
    return {"start": cue.start, "end": cue.end, "text": cue.text, "source": cue.source,
            "words": [asdict(word) for word in cue.words]}


def made(clip: Path, out: Path) -> Row:
    """One job, timed stage by stage."""
    truth = json.loads((clip / "truth.json").read_text(encoding="utf-8"))
    job = Job(clip / "clip.wav", target=truth["target"], burn=False, out_dir=out,
              cache_dir=out / "cache")
    stages: list[tuple[str, float]] = []
    found = collecting()
    cues, issues = pipeline.run(job, lambda stage: stages.append((stage, time.monotonic())))
    seconds = {name: round(later - at, 1)
               for (name, at), (_next, later) in pairwise(stages)}
    return {"clip": clip.name, "seconds": seconds, "cues": [line(cue) for cue in cues],
            "doubts": None if found.doubts is None else asdict(found.doubts),
            "notes": found.notes(cues, issues), "guards": found.guards}


def same_hearing(clip: str, label: str, other: str) -> None:
    """The other run's hearing of the clip put where this run looks for a kept one."""
    heard = RUNS / other / clip / "cache" / "clip" / "heard.json"
    if not heard.exists():
        return
    kept = json.loads(heard.read_text(encoding="utf-8"))
    target = RUNS / label / clip / "cache" / "clip"
    target.mkdir(parents=True, exist_ok=True)
    (target / "heard.json").write_text(json.dumps({**kept, "added": []}, ensure_ascii=False),
                                       encoding="utf-8")


def run(clip: Path, label: str, hearing: str = "") -> Row:
    out = RUNS / label / clip.name
    kept = out / "result.json"
    if kept.exists():
        return dict(json.loads(kept.read_text(encoding="utf-8")))
    out.mkdir(parents=True, exist_ok=True)
    if hearing:
        same_hearing(clip.name, label, hearing)
    started = time.monotonic()
    with (out / "log.txt").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
        try:
            row = made(clip, out)
        except Exception as error:  # a clip that fails is a result too: said, then the next
            traceback.print_exc(file=log)
            row = {"clip": clip.name, "error": f"{type(error).__name__}: {error}"[:300]}
    row["took"] = round(time.monotonic() - started, 1)
    kept.write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("clips", nargs="*")
    parser.add_argument("--label", default="first")
    parser.add_argument("--hearing", default="")
    args = parser.parse_args()
    names = args.clips or sorted(p.name for p in CLIPS.iterdir() if (p / "truth.json").exists())
    for name in names:
        row = run(CLIPS / name, args.label, args.hearing)
        said = row.get("error") or f"{len(row['cues'])} lines, stages {row['seconds']}"
        print(f"{name}: {row['took']} s, {said}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
