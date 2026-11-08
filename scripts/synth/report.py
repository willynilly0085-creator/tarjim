"""Reading a bench: a summary table per fault (or clip), the worst cells, and a package's
acceptance against a baseline (acceptance.json).

acceptance.json:
    "default": every metric of bench.METRICS no worse than the baseline's same cell, within the
               baseline's band (results/BASELINE.band.json) or bench.TOLERANCE, cpu_s_per_min and
               peak_mb within bench.RELATIVE of the baseline, plus the "always" rules.
    "packages": {PKG: [rule, ...]}, a rule being {"metric", "where": {field: value or [values]},
               and one of "at_most", "at_least", "at_most_plus" (<= baseline + n),
               "at_most_times" (<= k x baseline), "equals"}.
"""
import json
import statistics
from collections import defaultdict
from typing import Any

import bench

Row = dict[str, Any]
COLUMNS = [("cells", "n"), ("errors", "err"), ("start_median", "med"), ("start_p95", "p95"),
           ("missing_seconds", "unshown_s"), ("duplicated_words", "dup"),
           ("early_cues", "early"), ("late_cues", "late"), ("rushed_cues", "rush"),
           ("stopped", "stopped"), ("speaker_accuracy", "spk"), ("extra_words", "extra"),
           ("on_silence", "silent"), ("flips", "flips"), ("letters_passes", "mms_max"),
           ("vad_runs", "vad"), ("oracle_calls", "calls")]


def values(rows: list[Row], metric: str) -> list[float]:
    return [v for r in rows if (v := bench.number(r.get(metric))) is not None]


def summed(rows: list[Row], metric: str) -> float:
    return sum(values(rows, metric))


def middle(rows: list[Row], metric: str) -> float | None:
    found = values(rows, metric)
    return statistics.median(found) if found else None


def mean(rows: list[Row], metric: str) -> float | None:
    found = values(rows, metric)
    return statistics.fmean(found) if found else None


def line(rows: list[Row]) -> dict[str, Any]:
    ok = [r for r in rows if r.get("ok")]
    passes = values(ok, "letters_passes")
    return {"cells": len(rows), "errors": len(rows) - len(ok),
            "start_median": middle(ok, "start_median"), "start_p95": middle(ok, "start_p95"),
            "missing_seconds": summed(ok, "missing_seconds"),
            "duplicated_words": summed(ok, "duplicated_words"),
            "early_cues": summed(ok, "early_cues"), "late_cues": summed(ok, "late_cues"),
            "rushed_cues": summed(ok, "rushed_cues"),
            "stopped": sum((bench.number(r.get("tail_seconds")) or 0.0) > bench.STOPPED
                           for r in ok),
            "speaker_accuracy": mean(ok, "speaker_accuracy"),
            "extra_words": summed(ok, "extra_words"), "on_silence": summed(ok, "on_silence"),
            "flips": summed(ok, "flips"), "letters_passes": max(passes) if passes else None,
            "vad_runs": mean(ok, "vad_runs"), "oracle_calls": summed(ok, "oracle_calls")}


def shown(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.0f}" if value.is_integer() else f"{value:.2f}"
    return str(value)


def grid(title: str, groups: dict[str, list[Row]]) -> None:
    head = [title] + [h for _, h in COLUMNS]
    body = [[name] + [shown(line(rows)[k]) for k, _ in COLUMNS] for name, rows in groups.items()]
    widths = [max(len(r[i]) for r in [head, *body]) for i in range(len(head))]
    for row in [head, *body]:
        print("| " + " | ".join(t.ljust(w) for t, w in zip(row, widths, strict=True)) + " |")


def badness(row: Row) -> float:
    """One number to rank cells by, all faults alike: unshown speech first."""
    if not row.get("ok"):
        return 1000.0
    n = lambda k: bench.number(row.get(k)) or 0.0  # noqa: E731
    spk = bench.number(row.get("speaker_accuracy"))
    return (100 * n("missing_share") + 10 * min(n("start_p95"), 10.0) + 2 * n("duplicated_words")
            + 3 * (n("early_cues") + n("late_cues")) + 0.5 * (n("extra_words") + n("on_silence"))
            + 30 * (1 - (1.0 if spk is None else spk)) + n("flips")
            + 2 * max(0.0, n("tail_seconds")))


def worst(rows: list[Row], count: int) -> None:
    print(f"\nworst {count} cells:")
    for row in sorted(rows, key=badness, reverse=True)[:count]:
        if not row.get("ok"):
            print(f"  {badness(row):7.1f}  {row['clip']} {row['fault']} local={row['local']} "
                  f"oracle={row['oracle']}: ERROR {row.get('error')}")
            continue
        print(f"  {badness(row):7.1f}  {row['clip']} {row['fault']} local={row['local']} "
              f"oracle={row['oracle']}: miss {row.get('missing_seconds')} s "
              f"({row.get('missing_count')} words), p95 {row.get('start_p95')}, "
              f"dup {row.get('duplicated_words')}, early/late {row.get('early_cues')}/"
              f"{row.get('late_cues')}, extra {row.get('extra_words')}, silent "
              f"{row.get('on_silence')}, spk {row.get('speaker_accuracy')}, flips "
              f"{row.get('flips')}, tail {row.get('tail_seconds')}, calls "
              f"{row.get('oracle_calls')}")


def summary(rows: list[Row], by: str, count: int) -> None:
    groups: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(by))].append(row)
    grid(by, dict(groups))
    grid("all", {"all": rows})
    sites: dict[str, int] = defaultdict(int)
    for row in rows:
        for site, n in (row.get("vad_sites") or {}).items():
            sites[site] += n
    print(f"\nvoice detector calls by site: {dict(sites)}")
    over = [r for r in rows if (bench.number(r.get("letters_passes")) or 0) > 1]
    print(f"cells hearing the clip's letters more than once: {len(over)}")
    worst(rows, count)


def matches(row: Row, where: dict[str, Any]) -> bool:
    for k, want in where.items():
        have = row.get(k, bench.DEFAULTS.get(k))
        if have not in (want if isinstance(want, list) else [want]):
            return False
    return True


def broken(rule: dict[str, Any], row: Row, base: Row | None) -> str | None:
    """Why the cell breaks the rule, or None."""
    m = rule["metric"]
    value, old = bench.number(row.get(m)), bench.number((base or {}).get(m))
    if value is None:
        return f"{m} not measured"
    limits = {"at_most": rule.get("at_most"), "at_least": rule.get("at_least"),
              "equals": rule.get("equals")}
    if "at_most_plus" in rule and old is not None:
        limits["at_most"] = old + rule["at_most_plus"]
    if "at_most_times" in rule and old is not None:
        limits["at_most"] = old * rule["at_most_times"]
    if limits["at_most"] is not None and value > limits["at_most"] + bench.SAME:
        return f"{m} {value:g} > {limits['at_most']:g}"
    if limits["at_least"] is not None and value < limits["at_least"] - bench.SAME:
        return f"{m} {value:g} < {limits['at_least']:g}"
    if limits["equals"] is not None and abs(value - limits["equals"]) > bench.SAME:
        return f"{m} {value:g} != {limits['equals']:g}"
    return None


def verdict(row: Row, base: Row | None, rules: list[dict], spec: dict, band: dict) -> list[str]:
    failed: list[str] = []
    if base is not None:
        for m in spec.get("default", {}).get("metrics", list(bench.METRICS)):
            if bench.worse(m, base.get(m), row.get(m), band):
                failed.append(f"{m} {base.get(m)}->{row.get(m)}")
    for rule in rules:
        if matches(row, rule.get("where", {})) and (why := broken(rule, row, base)):
            failed.append(why)
    return failed


def accept(package: str, label: str, baseline: str) -> bool:
    spec = json.loads(bench.ACCEPTANCE.read_text(encoding="utf-8"))
    if package not in spec.get("packages", {}):
        raise SystemExit(f"{package} is not in {bench.ACCEPTANCE}")
    rules = [*spec.get("default", {}).get("always", []), *spec["packages"][package]]
    base = {bench.key_of(r): r for r in bench.load(baseline)}
    banded = bench.cell_band(baseline)
    rows = bench.load(label)
    failed = 0
    for row in rows:
        key = bench.key_of(row)
        why = verdict(row, base.get(key), rules, spec, banded(key))
        failed += bool(why)
        print(f"{'FAIL' if why else 'PASS'}  {' '.join(map(str, key))}"
              f"{'  ' + '; '.join(why) if why else ''}{'' if key in base else '  (new cell)'}")
    gone = [k for k in base if k not in {bench.key_of(r) for r in rows}]
    print(f"\n{package} on {label} against {baseline}: {len(rows) - failed}/{len(rows)} cells pass"
          f"{f', {len(gone)} baseline cells not run' if gone else ''}")
    print("OVERALL PASS" if not failed else "OVERALL FAIL")
    return not failed
