"""The timing bench: clips x faults x settings scored against the truth, and benches compared.

    python bench.py run LABEL [--tier smoke|gate|gate4|full|cpu] [--clips a,b] [--faults f1,f2+f3]
                              [--local on,off,wrong] [--oracle good,none,invent,quota] [--seed N]
                              [--voiceprint on|off] [--letters none|weak|sparse|wrong] [--cpu]
                              [--rerun] [--resume] [--clips-dir DIR]
    python bench.py table LABEL
    python bench.py summary LABEL [--by fault|clip] [--worst N]
    python bench.py band LABEL [OTHER]      noise band: |run - rerun| per cell and metric
    python bench.py compare A B [--key clip,fault,...]
    python bench.py accept PKG LABEL BASELINE   thresholds in acceptance.json, PASS/FAIL

A run writes results/LABEL.json after every cell, so a bench stopped half way keeps what it did
(--resume skips the cells already there). Without --tier the cells are every clip x fault x
local x oracle; faults: --faults, else the scenario's own, else every fault there is.
The band is max(TOLERANCE, |run - rerun| at the same seed): from each row's "rerun" (--rerun), or
from a second label run at the same seeds. compare and accept work on paired per-cell differences.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run  # first: it sets the environment before tarjim is imported
import score
import tiers
from faults import FAULTS

RESULTS = run.SYNTH / "results"
ACCEPTANCE = Path(__file__).resolve().parent / "acceptance.json"
KEY = ("clip", "fault", "local", "oracle", "seed", "voiceprint", "letters", "cpu")
DEFAULTS = {"voiceprint": "on", "letters": "none", "cpu": False}
# metric: +1 higher is better, -1 lower is better, 0 closer to zero is better
METRICS = {"ok": 1, "matched": 1, "start_median": -1, "start_p95": -1, "over_0_5": -1,
           "over_1_5": -1, "missing_count": -1, "missing_seconds": -1, "early_cues": -1,
           "late_cues": -1, "duplicated_words": -1, "rushed_cues": -1, "tail_seconds": 0,
           "speaker_accuracy": 1, "short_cues": -1, "overlapping_cues": -1, "slope": 0,
           "extra_words": -1, "on_silence": -1, "background_words": -1, "flips": -1,
           "letters_passes": -1, "vad_runs": -1, "oracle_calls": -1, "oracle_requests": -1,
           "oracle_audio_s": -1, "cpu_s_per_min": -1, "peak_mb": -1}
TOLERANCE = {"start_median": 0.02, "start_p95": 0.05, "over_0_5": 0.01, "over_1_5": 0.01,
             "matched": 0.005, "missing_seconds": 0.2, "tail_seconds": 0.2,
             "speaker_accuracy": 0.005, "slope": 0.05, "oracle_audio_s": 0.5}
RELATIVE = {"cpu_s_per_min": 0.3, "peak_mb": 0.15}  # shares of A: machine noise, not code
STOPPED = 1.0  # seconds of speech after the last cue: the subtitles stopped early

SAME = 1e-9
Row = dict[str, Any]
Key = tuple[Any, ...]


def scenario_faults() -> dict[str, list[str]]:
    try:
        import scenarios
    except Exception as error:  # the bench runs without the scenarios too
        print(f"bench: scenarios.py not read ({type(error).__name__}: {error})")
        return {}
    return {s.name: list(s.faults) for s in getattr(scenarios, "SCENARIOS", [])
            if getattr(s, "faults", None)}


def clips_in(folder: Path, chosen: str) -> list[Path]:
    found = sorted(p for p in folder.iterdir() if (p / "truth.json").exists()) \
        if folder.exists() else []
    names = [n for n in chosen.split(",") if n]
    return [p for p in found if not names or p.name in names]


def split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def save(label: str, rows: list[Row]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{label}.json"
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def planned(args: argparse.Namespace, clips: list[Path]) -> list[tiers.Cell]:
    if args.tier:
        faults = split(args.faults) or list(FAULTS)
        return tiers.cells(args.tier, [c.name for c in clips], faults)
    own = scenario_faults()
    return [(clip.name, fault, local, oracle, args.seed) for clip in clips
            for fault in split(args.faults) or own.get(clip.name) or list(FAULTS)
            for local in split(args.local) for oracle in split(args.oracle)]


def bench(args: argparse.Namespace) -> None:
    clips = clips_in(Path(args.clips_dir), args.clips)
    if not clips:
        raise SystemExit(f"no clips with truth.json in {args.clips_dir}")
    run.start(args.cpu or args.tier == "cpu")
    folder = {c.name: c for c in clips}
    rows: list[Row] = load(args.label) if args.resume and (RESULTS / f"{args.label}.json").exists() \
        else []
    done = {key_of(r) for r in rows}
    todo = planned(args, clips)
    for clip, fault, local, oracle, seed in todo:
        setting = run.Setting(args.label, local, oracle, seed, args.voiceprint == "on",
                              args.letters, args.cpu or args.tier == "cpu", args.rerun)
        if key_of({"clip": clip, "fault": fault, **setting.keys()}) in done:
            continue
        row = run.run_one(folder[clip], fault, setting)
        rows.append(row)
        path = save(args.label, rows)
        state = "ok" if row["ok"] else f"ERROR {row.get('error')}"
        print(f"[{len(rows)}/{len(todo)}] {clip} {fault} local={local} oracle={oracle} "
              f"seed={seed}: {state} ({row['seconds']} s)", flush=True)
    score.table(rows)
    print(f"\n{RESULTS / f'{args.label}.json'}")


def load(label: str) -> list[Row]:
    path = Path(label) if label.endswith(".json") else RESULTS / f"{label}.json"
    rows = list(json.loads(path.read_text(encoding="utf-8")))
    for row in rows:
        for k, v in DEFAULTS.items():
            row.setdefault(k, v)
    return rows


def key_of(row: Row, key: tuple[str, ...] = KEY) -> Key:
    return tuple(row.get(k, DEFAULTS.get(k)) for k in key)


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    return float(value) if isinstance(value, (int, float)) else None


def gain(metric: str, a: Any, b: Any) -> float | None:
    """How much better B is than A on the metric (negative: worse); None when either is missing."""
    x, y = number(a), number(b)
    if x is None or y is None:
        return None
    direction = METRICS[metric]
    return abs(x) - abs(y) if direction == 0 else (y - x) * direction


def room(metric: str, a: Any, band: dict[str, float] | None) -> float:
    base = max(TOLERANCE.get(metric, 0.0), (band or {}).get(metric, 0.0))
    x = number(a)
    return max(base, RELATIVE[metric] * abs(x)) if metric in RELATIVE and x is not None else base


def worse(metric: str, a: Any, b: Any, band: dict[str, float] | None = None) -> bool:
    if number(a) is not None and number(b) is None:
        return True  # a metric B could not measure at all
    change = gain(metric, a, b)
    return change is not None and change < -room(metric, a, band) - SAME


def bands(label: str) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """The band file's per-metric band and per-cell bands, empty when there is none."""
    path = RESULTS / f"{label}.band.json"
    if not path.exists():
        return {}, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("metrics", {}), data.get("cells", {})


def cell_band(label: str) -> Any:
    whole, per = bands(label)
    return lambda key: {**whole, **per.get("|".join(map(str, key)), {})}


def band(label: str, other: str | None) -> None:
    rows = load(label)
    pairs: list[tuple[Row, Row]]
    if other:
        theirs = {key_of(r): r for r in load(other)}
        pairs = [(r, theirs[key_of(r)]) for r in rows if key_of(r) in theirs]
    else:
        pairs = [(r, r["rerun"]) for r in rows if isinstance(r.get("rerun"), dict)]
    if not pairs:
        raise SystemExit("no pairs: run with --rerun, or name a second label at the same seeds")
    cells: dict[str, dict[str, float]] = {}
    whole: dict[str, float] = dict.fromkeys(METRICS, 0.0)
    for a, b in pairs:
        diffs = {m: abs(x - y) for m in METRICS
                 if (x := number(a.get(m))) is not None and (y := number(b.get(m))) is not None}
        cells["|".join(map(str, key_of(a)))] = {m: round(v, 4) for m, v in diffs.items() if v}
        for m, v in diffs.items():
            whole[m] = max(whole[m], v)
    metrics = {m: round(max(TOLERANCE.get(m, 0.0), v), 4) for m, v in whole.items()}
    out = RESULTS / f"{label}.band.json"
    out.write_text(json.dumps({"source": other or "rerun", "pairs": len(pairs),
                               "metrics": metrics, "cells": cells}, indent=1), encoding="utf-8")
    moved = {k: v for k, v in cells.items() if v}
    print(f"{len(pairs)} pairs, {len(moved)} cell(s) differ")
    for m, v in metrics.items():
        print(f"  {m:18} {v}")
    print(out)


def paired(a_label: str, b_label: str, key: tuple[str, ...]) -> list[tuple[Key, Row, Row]]:
    a_rows = {key_of(r, key): r for r in load(a_label)}
    b_rows = {key_of(r, key): r for r in load(b_label)}
    return [(k, a_rows[k], b_rows[k]) for k in a_rows if k in b_rows]


def compare(a_label: str, b_label: str, key: tuple[str, ...] = KEY) -> None:
    """B against A cell by cell, matched on `key`: per metric the summed paired gain and how
    many cells moved past the band either way."""
    shared = paired(a_label, b_label, key)
    banded = cell_band(a_label)
    print(f"{len(shared)} cells in both")
    print(f"\n{'metric':18} {'cells':>6} {'sum gain':>10} {'mean':>8} {'better':>7} {'worse':>6}")
    for metric in METRICS:
        gains = [(g, k, a, b) for k, a, b in shared
                 if (g := gain(metric, a.get(metric), b.get(metric))) is not None]
        up = sum(g > room(metric, a.get(metric), banded(k)) + SAME for g, k, a, _ in gains)
        down = sum(worse(metric, a.get(metric), b.get(metric), banded(k)) for _, k, a, b in gains)
        total = sum(g for g, *_ in gains)
        mean = total / len(gains) if gains else 0.0
        print(f"{metric:18} {len(gains):6d} {total:10.2f} {mean:8.3f} {up:7d} {down:6d}")
    print("\ncells where B is worse than the band:")
    count = 0
    for k, a, b in shared:
        lost = [f"{m} {score.cell(a.get(m))}->{score.cell(b.get(m))}" for m in METRICS
                if worse(m, a.get(m), b.get(m), banded(k))]
        if lost:
            count += 1
            print(f"  {' '.join(str(x) for x in k)}: {'; '.join(lost)}")
    print(f"{count} cell(s) worse in B" if count else "  none")


def parsed() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split(chr(10))[0])
    sub = parser.add_subparsers(dest="command", required=True)
    go = sub.add_parser("run")
    go.add_argument("label")
    go.add_argument("--tier", choices=tiers.TIERS, default="")
    go.add_argument("--clips", default="")
    go.add_argument("--faults", default="")
    go.add_argument("--local", default="on,off")
    go.add_argument("--oracle", default="good,none")
    go.add_argument("--seed", type=int, default=0)
    go.add_argument("--voiceprint", choices=("on", "off"), default="on")
    go.add_argument("--letters", choices=("none", "weak", "sparse", "wrong"), default="none")
    go.add_argument("--cpu", action="store_true")
    go.add_argument("--rerun", action="store_true")
    go.add_argument("--resume", action="store_true")
    go.add_argument("--clips-dir", default=str(run.SYNTH / "clips"))
    sub.add_parser("table").add_argument("label")
    shown = sub.add_parser("summary")
    shown.add_argument("label")
    shown.add_argument("--by", default="fault")
    shown.add_argument("--worst", type=int, default=10)
    noise = sub.add_parser("band")
    noise.add_argument("label")
    noise.add_argument("other", nargs="?")
    both = sub.add_parser("compare")
    both.add_argument("a")
    both.add_argument("b")
    both.add_argument("--key", default=",".join(KEY), help="fields a cell is matched on")
    gate = sub.add_parser("accept")
    gate.add_argument("package")
    gate.add_argument("label")
    gate.add_argument("baseline")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    args = parsed()
    if args.command == "run":
        bench(args)
    elif args.command == "table":
        score.table(load(args.label))
    elif args.command == "summary":
        import report

        report.summary(load(args.label), args.by, args.worst)
    elif args.command == "band":
        band(args.label, args.other)
    elif args.command == "compare":
        compare(args.a, args.b, tuple(split(args.key)))
    else:
        import report

        sys.exit(0 if report.accept(args.package, args.label, args.baseline) else 1)


if __name__ == "__main__":
    main()
