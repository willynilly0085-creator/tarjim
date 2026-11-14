"""A run of the real-speech bench scored on what a subtitle owes: heard right, and on screen
while it is said (the meaning is judged in judge.py), and whether the lines the job itself
doubts (tarjim/doubts.py) are the lines that are wrong.

Hearing: the usual word error count against what people wrote was said (words.py).
Timing, against where each sentence was laid in the clip (build.py), a truth no aligner made:
- the first word of a sentence against the sentence's start, and its last word against its end
  (only the edges the clip's truth is sure of, build.edges);
- words timed more than OUT outside their own sentence;
- what a viewer sees: the subtitle that opens a sentence coming up more than LATE after it
  begins or before it, and the one that closes it going more than GONE before it ends. A
  subtitle that carries the end of the sentence before too is not asked when it came up.
The job's doubts: of the lines it listed, how many are wrong (precision), and of the wrong
lines, how many it listed (recall); the same for single words (listen/witness.alone).

    python score.py [--label L]
"""
import argparse
import json
from collections import Counter
from statistics import median
from typing import Any

from paths import CLIPS, RUNS, prepare

prepare()

from words import DEL, INS, OK, SUB, plain, steps  # noqa: E402

LATE, GONE, OUT = 0.5, 0.3, 0.5
Row = dict[str, Any]


def alone(word: Row) -> bool | None:
    if word.get("backed") is None and word.get("local") is None:
        return None
    return (word.get("backed") or 0) + bool(word.get("local")) < 2  # noqa: PLR2004


def units(truth: Row, result: Row) -> tuple[list[tuple[str, int]], list[tuple[str, int, Row]]]:
    """What was said, each unit with its sentence; what was written, with its line and word."""
    code = truth["language"].split("_")[0].replace("cmn", "zh")
    said = [(unit, k) for k, sentence in enumerate(truth["sentences"])
            for unit in plain(sentence["text"], code)]
    wrote = [(unit, c, word) for c, cue in enumerate(result["cues"])
             for word in cue["words"] for unit in plain(word["text"], code)]
    return said, wrote


def tally(flagged: bool | None, wrong: bool, counts: Counter[str]) -> None:
    if flagged is None:
        counts["unknown"] += 1
    else:
        counts[("t" if flagged == wrong else "f") + ("p" if flagged else "n")] += 1


def share(counts: Counter[str]) -> Row:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {**counts, "precision": round(tp / (tp + fp), 2) if tp + fp else None,
            "recall": round(tp / (tp + fn), 2) if tp + fn else None}


class Scored:
    """One clip: the path from what was said to what was written, and what it tells."""

    def __init__(self, truth: Row, result: Row) -> None:
        self.truth, self.result = truth, result
        self.said, self.wrote = units(truth, result)
        self.path = steps([unit for unit, _k in self.said], [unit for unit, *_ in self.wrote])
        # each said unit's written word and line, when one stands for it
        self.stood = {step.said: self.wrote[step.wrote] for step in self.path
                      if step.said is not None and step.wrote is not None}

    def hearing(self) -> Row:
        kinds = Counter(step.kind for step in self.path)
        errors = kinds[SUB] + kinds[INS] + kinds[DEL]
        wrong = [(self.said[s.said][0] if s.said is not None else "",
                  self.wrote[s.wrote][0] if s.wrote is not None else "")
                 for s in self.path if s.kind != OK]
        return {"said": len(self.said), "errors": errors, "sub": kinds[SUB], "ins": kinds[INS],
                "del": kinds[DEL], "wer": round(errors / max(1, len(self.said)), 4),
                "wrong": wrong[:40]}

    def wrong_lines(self) -> set[int]:
        """The lines with a unit not said, or next to one said and not written."""
        found, line = set(), 0
        for step in self.path:
            if step.wrote is not None:
                line = self.wrote[step.wrote][1]
            if step.kind != OK:
                found.add(line)
        return found

    def doubted(self) -> Row:
        words, lines = Counter[str](), Counter[str]()
        for step in self.path:
            if step.wrote is not None:
                tally(alone(self.wrote[step.wrote][2]), step.kind != OK, words)
        listed = set((self.result.get("doubts") or {}).get("hearing") or [])
        wrong = self.wrong_lines()
        for c in range(len(self.result["cues"])):
            tally(c + 1 in listed, c in wrong, lines)
        return {"words": share(words), "lines": share(lines)}

    def sentence(self, k: int) -> Row | None:
        """Where sentence k's first and last words and its subtitles are, against the truth."""
        mine = [i for i, (_unit, owner) in enumerate(self.said) if owner == k]
        held = [(i, self.stood[i]) for i in mine if i in self.stood]
        if not held:
            return None
        fact, cues = self.truth["sentences"][k], self.result["cues"]
        first, last = held[0][1], held[-1][1]
        before = {self.said[i][1] for i, (_u, c, _w) in self.stood.items() if c == first[1]}
        begun = held[0][0] == mine[0] and fact["sure_start"]
        ended = held[-1][0] == mine[-1] and fact["sure_end"]
        opens = begun and min(before) >= k
        return {"first": first[2]["start"] - fact["start"] if begun else None,
                "last": last[2]["end"] - fact["end"] if ended else None,
                "up": cues[first[1]]["start"] - fact["start"] if opens else None,
                "down": cues[last[1]]["end"] - fact["end"] if ended else None,
                "lines": (first[1], last[1]),
                "out": sum(not fact["start"] - OUT <= (w["start"] + w["end"]) / 2
                           <= fact["end"] + OUT for _i, (_u, _c, w) in held), "held": len(held)}

    def timing(self) -> Row:
        found = [s for k in range(len(self.truth["sentences"])) if (s := self.sentence(k))]
        edges = [abs(s[key]) for s in found for key in ("first", "last") if s[key] is not None]
        ups = [s["up"] for s in found if s["up"] is not None]
        downs = [s["down"] for s in found if s["down"] is not None]
        listed, lines = set((self.result.get("doubts") or {}).get("timing") or []), Counter[str]()
        for s in found:
            if s["up"] is not None:
                tally(s["lines"][0] + 1 in listed, abs(s["up"]) > LATE, lines)
            if s["down"] is not None:
                tally(s["lines"][1] + 1 in listed, s["down"] < -GONE, lines)
        return {"sentences": len(found), "edges": len(edges),
                "edge_median": round(median(edges), 3) if edges else None,
                "edge_worst": round(max(edges), 2) if edges else None,
                "edge_over": sum(e > LATE for e in edges),
                "out": sum(s["out"] for s in found), "held": sum(s["held"] for s in found),
                "opened": len(ups), "late": sum(u > LATE for u in ups),
                "early": sum(u < -LATE for u in ups),
                "closed": len(downs), "gone": sum(d < -GONE for d in downs),
                "doubted": share(lines)}


def scored(name: str, label: str) -> Row | None:
    kept = RUNS / label / name / "result.json"
    if not kept.exists():
        return None
    truth = json.loads((CLIPS / name / "truth.json").read_text(encoding="utf-8"))
    result = json.loads(kept.read_text(encoding="utf-8"))
    if "error" in result:
        return {"clip": name, "error": result["error"]}
    one = Scored(truth, result)
    return {"clip": name, "duration": truth["duration"], "took": result["took"],
            "seconds": result["seconds"], "lines": len(result["cues"]),
            "hearing": one.hearing(), "timing": one.timing(), "doubted": one.doubted()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="first")
    label = parser.parse_args().label
    rows = [row for clip in sorted(CLIPS.iterdir()) if (row := scored(clip.name, label))]
    (RUNS / label / "scores.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    for row in rows:
        if "error" in row:
            print(f"{row['clip']:18} FAILED {row['error'][:90]}")
            continue
        h, t = row["hearing"], row["timing"]
        print(f"{row['clip']:18} {row['duration']:6.0f}s took {row['took']:5.0f}s | wer "
              f"{h['wer']:.3f} ({h['errors']}/{h['said']}) | edges med {t['edge_median']} worst "
              f"{t['edge_worst']} over {t['edge_over']}/{t['edges']} | out {t['out']}/{t['held']}"
              f" | late {t['late']} early {t['early']} of {t['opened']}, gone {t['gone']}"
              f"/{t['closed']}")


if __name__ == "__main__":
    main()
