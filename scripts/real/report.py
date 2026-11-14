"""One table of the three for a run of the real-speech bench, or two runs side by side.

Per clip and in all: hearing (words wrong of words said), timing (sentence edges more than half
a second off, words outside their own sentence, subtitles that come up early or late or go
before the sentence ends), meaning (the judge's verdicts, judge.py), and the seconds a job took
beside the clip's length. Then how well the job's own doubts point at what is wrong.

    python report.py first [second]      written to reports/<labels>.md and printed
"""
import json
import sys
from collections import Counter
from typing import Any

from paths import REAL, RUNS

Row = dict[str, Any]
VERDICTS = ("right", "small", "wrong")


def meaning(label: str, clip: str) -> Row:
    """The judge's verdicts for the clip, and its sentences the job itself listed."""
    kept = RUNS / label / clip / "meaning.json"
    if not kept.exists():
        return {}
    rows = json.loads(kept.read_text(encoding="utf-8"))
    result = json.loads((RUNS / label / clip / "result.json").read_text(encoding="utf-8"))
    listed = set((result.get("doubts") or {}).get("meaning") or [])
    counts = Counter(row["meaning"] for row in rows)
    told = Counter[str]()
    for row in rows:
        flagged, wrong = bool(listed & set(row["lines"])), row["meaning"] != "right"
        told[("t" if flagged == wrong else "f") + ("p" if flagged else "n")] += 1
    return {**{v: counts[v] for v in VERDICTS},
            "literal": sum(bool(r.get("literal")) for r in rows),
            "left_out": sum(bool(r.get("left_out")) for r in rows),
            "added": sum(bool(r.get("added")) for r in rows),
            "by_hearing": sum(r.get("cause") == "hearing" for r in rows), "told": told}


def cell(row: Row, label: str) -> str:
    if "error" in row:
        return f"FAILED: {row['error'][:60]}"
    h, t, m = row["hearing"], row["timing"], meaning(label, row["clip"])
    judged = f"{m['wrong']}/{m['small']}/{m['right']}" if m else "-"
    return (f"{100 * h['wer']:.1f}% ({h['errors']}/{h['said']}) | {t['edge_over']}/{t['edges']} "
            f"| {t['out']}/{t['held']} | {t['late'] + t['early']}/{t['opened']} "
            f"| {t['gone']}/{t['closed']} | {judged} | {row['took']:.0f}/{row['duration']:.0f}")


def total(rows: list[Row], label: str) -> Row:
    """Everything added up over the clips that ran."""
    done, found = [r for r in rows if "error" not in r], Counter[str]()
    for row in done:
        h, t, d = row["hearing"], row["timing"], row["doubted"]
        found.update({"errors": h["errors"], "said": h["said"], "edge_over": t["edge_over"],
                      "edges": t["edges"], "out": t["out"], "held": t["held"],
                      "off": t["late"] + t["early"], "opened": t["opened"], "gone": t["gone"],
                      "closed": t["closed"], "took": row["took"], "duration": row["duration"]})
        for kind, counts in (("w", d["words"]), ("l", d["lines"]), ("t", t["doubted"])):
            found.update({f"{kind}_{key}": counts.get(key, 0) for key in ("tp", "fp", "fn", "tn")})
        m = meaning(label, row["clip"])
        found.update({key: m.get(key, 0) for key in (*VERDICTS, "literal", "left_out", "added",
                                                     "by_hearing")})
        found.update({f"m_{key}": value for key, value in m.get("told", {}).items()})
    return dict(found)


def pointed(found: Row, kind: str) -> str:
    tp, fp, fn = found.get(f"{kind}_tp", 0), found.get(f"{kind}_fp", 0), found.get(f"{kind}_fn", 0)
    right = f"{tp} of {tp + fp} listed are wrong" if tp + fp else "none listed"
    return f"{right}; {tp} of {tp + fn} wrong ones are listed"


def summary(label: str, rows: list[Row]) -> list[str]:
    f = total(rows, label)
    return [f"### {label}: {len(rows)} clips, {f.get('duration', 0) / 60:.0f} minutes of speech",
            f"- hearing: {f['errors']} of {f['said']} words wrong "
            f"({100 * f['errors'] / max(1, f['said']):.1f}%)",
            f"- timing: {f['edge_over']} of {f['edges']} sentence edges over 0.5 s off; "
            f"{f['out']} of {f['held']} words outside their sentence; {f['off']} of {f['opened']} "
            f"subtitles come up over 0.5 s early or late; {f['gone']} of {f['closed']} go over "
            "0.3 s before the sentence ends",
            f"- meaning (judge): {f.get('wrong', 0)} wrong, {f.get('small', 0)} slightly off, "
            f"{f.get('right', 0)} right; {f.get('by_hearing', 0)} of the not-right from hearing; "
            f"{f.get('literal', 0)} word for word, {f.get('left_out', 0)} with something left "
            f"out, {f.get('added', 0)} with something added",
            f"- time: {f['took']:.0f} s of work for {f['duration']:.0f} s of sound",
            f"- the job's doubts, hearing by word: {pointed(f, 'w')}",
            f"- the job's doubts, hearing by line: {pointed(f, 'l')}",
            f"- the job's doubts, timing by line: {pointed(f, 't')}",
            f"- the job's doubts, meaning by sentence: {pointed(f, 'm')}", ""]


def main() -> None:
    labels = sys.argv[1:] or ["first"]
    scores = {label: {row["clip"]: row for row in json.loads(
        (RUNS / label / "scores.json").read_text(encoding="utf-8"))} for label in labels}
    clips = sorted(set.intersection(*(set(found) for found in scores.values())))
    lines = ["Columns per run: words wrong | sentence edges over 0.5 s | words outside their "
             "sentence | subtitles up early or late | gone before the end | meaning "
             "wrong/slightly off/right | seconds of work/of sound", ""]
    for clip in clips:
        lines.append(f"**{clip}**")
        lines += [f"- {label}: {cell(scores[label][clip], label)}" for label in labels]
    lines.append("")
    for label in labels:
        lines += summary(label, [scores[label][clip] for clip in clips])
    out = REAL / "reports" / f"{'-'.join(labels)}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
