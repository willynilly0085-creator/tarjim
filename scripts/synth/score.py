"""A run's transcript words and cues scored against the clip's truth.

Words are matched to truth words by text, in order (truth words sentence by sentence), and among
matchings of as many words the closest in time. A truth word is shown when a cue says it and is
on screen while it is said (0.3 s either way); it is shown twice when two cues near it say it
with a neighbour of it (pairs of words, so a common word alone does not count).

    python score.py <run folder> [<clip folder>]   (re-scores a run from its words.json, cues.json)
"""
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Callable
from itertools import pairwise, permutations
from pathlib import Path
from typing import Any

SLACK = 0.3  # a cue on screen this close to a word shows it
OFF = 1.0  # a cue this far before or after its first truth word is early or late
RUSHED = 5.5  # words a second
SHORT = 0.9  # seconds on screen
NEAR = 10.0  # seconds: a second cue saying a word this close is the word said twice
LATE, VERY_LATE = 0.5, 1.5
BRUTE_LIMIT = 6  # labels tried in every assignment without scipy
TIME_CAP = 60.0  # seconds: words further apart than this are all as far, for the matching
SAME = 1e-12
OTHER_SPEAKER = 1000.0  # seconds: a word is another speaker's sentence's only when none is near

Row = dict[str, Any]
TABLE = [("ok", "ok"), ("clip", "clip"), ("fault", "fault"), ("local", "loc"),
         ("oracle", "orc"), ("matched", "match"), ("start_median", "med"),
         ("start_p95", "p95"), ("over_0_5", ">.5"), ("over_1_5", ">1.5"),
         ("missing_count", "miss"), ("missing_seconds", "miss_s"), ("early_cues", "early"),
         ("late_cues", "late"), ("duplicated_words", "dup"), ("rushed_cues", "rush"),
         ("tail_seconds", "tail"), ("speaker_accuracy", "spk"), ("short_cues", "short"),
         ("overlapping_cues", "ovl"), ("cues", "cues"), ("extra_words", "extra"),
         ("on_silence", "silent"), ("flips", "flips"), ("letters_passes", "mms"),
         ("vad_runs", "vad"), ("oracle_calls", "calls")]


def norm(text: str) -> str:
    return "".join(re.findall(r"[\w']+", text.lower()))


def pairs(words_a: list[Row], words_b: list[Row]) -> list[tuple[int, int]]:
    """Indices of equal words matched in order, as many as there are; among matchings of as
    many, the one whose words are closest in time, so a line said twice is matched to the copy
    said where it was heard (difflib took the first longest run, often the other copy)."""
    tokens_a, tokens_b = [norm(w["text"]) for w in words_a], [norm(w["text"]) for w in words_b]
    cost = 0.5 / (min(len(words_a), len(words_b)) + 1) / TIME_CAP  # all of it < one word

    def gain(i: int, j: int) -> float:
        apart = abs(float(words_a[i]["start"]) - float(words_b[j]["start"]))
        return 1.0 - cost * min(apart, TIME_CAP)

    rows = [[0.0] * (len(tokens_b) + 1)]
    for i, token in enumerate(tokens_a):
        above, row = rows[-1], [0.0]
        for j, other in enumerate(tokens_b):
            here = max(above[j + 1], row[j])
            row.append(max(here, above[j] + gain(i, j)) if token and token == other else here)
        rows.append(row)
    return walked(rows, tokens_a, tokens_b, gain)


def walked(rows: list[list[float]], tokens_a: list[str], tokens_b: list[str],
           gain: Callable[[int, int], float]) -> list[tuple[int, int]]:
    """The matching `pairs` scored, read back from its table's corner."""
    i, j, out = len(tokens_a), len(tokens_b), []
    while i and j:
        same = bool(tokens_a[i - 1]) and tokens_a[i - 1] == tokens_b[j - 1]
        if same and abs(rows[i][j] - rows[i - 1][j - 1] - gain(i - 1, j - 1)) < SAME:
            out.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif rows[i - 1][j] >= rows[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return out[::-1]


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(share * (len(ordered) - 1)))]


def sentence_of(truth: Row) -> list[int]:
    """The truth sentence each truth word belongs to: same speaker, its time inside."""
    sentences = truth["sentences"]

    def distance(word: Row, s: Row) -> float:
        middle = (float(word["start"]) + float(word["end"])) / 2
        off = max(float(s["start"]) - middle, middle - float(s["end"]), 0.0)
        return off + (0.0 if s["speaker"] == word["speaker"] else OTHER_SPEAKER)

    return [min(range(len(sentences)), key=lambda i: distance(w, sentences[i]))
            for w in truth["words"]]


def spoken(truth: Row) -> list[Row]:
    """Truth words sentence by sentence, as a listener writes them: where two people talk at
    once, one's line and then the other's, not their words interleaved by time (an in-order
    match on interleaved words drops every word of the overlap)."""
    home = sentence_of(truth)
    starts = [float(s["start"]) for s in truth["sentences"]]
    order = sorted(range(len(home)),
                   key=lambda i: (starts[home[i]], home[i], float(truth["words"][i]["start"])))
    return [truth["words"][i] for i in order]


def word_timing(truth_words: list[Row], words: list[Row]) -> Row:
    matched = pairs(truth_words, words)
    errors = [abs(words[b]["start"] - truth_words[a]["start"]) for a, b in matched]
    if not errors:
        return {"matched": 0.0, "start_median": None, "start_p95": None, "over_0_5": None,
                "over_1_5": None}
    return {"matched": round(len(errors) / max(len(truth_words), 1), 3),
            "start_median": round(statistics.median(errors), 3),
            "start_p95": round(percentile(errors, 0.95), 3),
            "over_0_5": round(sum(e > LATE for e in errors) / len(errors), 3),
            "over_1_5": round(sum(e > VERY_LATE for e in errors) / len(errors), 3)}


def cue_words(cue: Row) -> list[Row]:
    return [w for part in cue.get("parts") or [] for w in part]


def on_screen(cue: Row, word: Row) -> bool:
    """On screen from the word's start to its middle (a synthetic word's end holds the voice's
    fade), 0.3 s either way."""
    middle = (float(word["start"]) + float(word["end"])) / 2
    return bool(cue["start"] - SLACK <= word["start"] and middle <= cue["end"] + SLACK)


def missing(truth_words: list[Row], cues: list[Row]) -> Row:
    said = [Counter(norm(w["text"]) for w in cue_words(c)) for c in cues]
    gone = [w for w in truth_words
            if not any(on_screen(c, w) and said[i][norm(w["text"])] for i, c in enumerate(cues))]
    return {"missing_count": len(gone),
            "missing_seconds": round(sum(w["end"] - w["start"] for w in gone), 2),
            "missing_share": round(len(gone) / max(len(truth_words), 1), 3)}


def duplicated(truth_words: list[Row], cues: list[Row]) -> int:
    """Words a cue shows that the in-order match left over, and that were said close by with a
    neighbour of theirs: the same speech shown a second time (a one-word cue: the word alone)."""
    tokens = [norm(w["text"]) for w in truth_words]
    flat = [(k, norm(w["text"])) for k, c in enumerate(cues) for w in cue_words(c)]
    used = {b for _, b in pairs(truth_words, [w for c in cues for w in cue_words(c)])}
    twice = 0
    for j, (k, token) in enumerate(flat):
        if j in used:
            continue
        cue = cues[k]
        near = [i for i, w in enumerate(truth_words)
                if cue["start"] - NEAR <= w["start"] <= cue["end"] + NEAR]
        said = {(tokens[i - 1], tokens[i]) for i in near if i > 0}
        mine = {(flat[j - 1][1], token)} if j > 0 and flat[j - 1][0] == k else set()
        if j + 1 < len(flat) and flat[j + 1][0] == k:
            mine.add((token, flat[j + 1][1]))
        alone = not mine and token in {tokens[i] for i in near}
        twice += bool(mine & said) or alone
    return twice


def owners(truth_words: list[Row], cues: list[Row]) -> list[list[int | None]]:
    """For each cue, for each of its words in order, the truth word it is (None: no match)."""
    flat = [(k, w) for k, c in enumerate(cues) for w in cue_words(c)]
    found = dict((b, a) for a, b in pairs(truth_words, [w for _, w in flat]))
    out: list[list[int | None]] = [[] for _ in cues]
    for index, (k, _) in enumerate(flat):
        out[k].append(found.get(index))
    return out


def placement(truth_words: list[Row], cues: list[Row], owned: list[list[int | None]]) -> Row:
    offsets = []
    for cue, mine in zip(cues, owned, strict=True):
        first = min((i for i in mine if i is not None), default=None)
        if first is not None:
            offsets.append(cue["start"] - truth_words[first]["start"])
    return {"early_cues": sum(o <= -OFF for o in offsets),
            "late_cues": sum(o >= OFF for o in offsets),
            "cue_offset_median": round(statistics.median(offsets), 3) if offsets else None}


def speaker_accuracy(truth_words: list[Row], cues: list[Row],
                     owned: list[list[int | None]]) -> float | None:
    """Each cue part: its majority truth speaker against its majority tarjim label, labels
    mapped to truth speakers by the best one-to-one assignment."""
    counts: Counter[tuple[str, str]] = Counter()
    for cue, mine in zip(cues, owned, strict=True):
        index = 0
        for part in cue.get("parts") or []:
            ids = [i for i in mine[index:index + len(part)] if i is not None]
            index += len(part)
            if ids and part:
                theirs = Counter(truth_words[i]["speaker"] for i in ids).most_common(1)[0][0]
                ours = Counter(label(w["speaker"]) for w in part).most_common(1)[0][0]
                counts[(ours, theirs)] += 1
    total = sum(counts.values())
    if not total:
        return None
    return round(best_assignment(counts) / total, 3)


def label(speaker: str) -> str:
    return re.sub(r"(?:^|(?<=\.))p\d+\.", "", speaker or "")


def best_assignment(counts: Counter[tuple[str, str]]) -> int:
    ours = sorted({o for o, _ in counts})
    theirs = sorted({t for _, t in counts})
    try:
        from scipy.optimize import linear_sum_assignment
    except ImportError:
        return brute_assignment(counts, ours, theirs)
    grid = [[counts[(o, t)] for t in theirs] for o in ours]
    rows, columns = linear_sum_assignment(grid, maximize=True)
    return int(sum(grid[r][c] for r, c in zip(rows, columns, strict=True)))


def brute_assignment(counts: Counter[tuple[str, str]], ours: list[str], theirs: list[str]) -> int:
    if len(ours) > BRUTE_LIMIT:  # greedy: each label to its most frequent truth speaker
        return sum(max(counts[(o, t)] for t in theirs) for o in ours)
    slots: list[str | None] = [*theirs, *([None] * len(ours))]
    return max(sum(counts[(o, t)] for o, t in zip(ours, choice, strict=False) if t is not None)
               for choice in set(permutations(slots, len(ours))))


def cue_shape(truth_words: list[Row], cues: list[Row]) -> Row:
    ordered = sorted(cues, key=lambda c: c["start"])
    rushed = sum(len(cue_words(c)) / max(c["end"] - c["start"], 0.01) > RUSHED for c in cues)
    last_cue = max((c["end"] for c in cues), default=0.0)
    last_word = max((w["end"] for w in truth_words), default=0.0)
    return {"cues": len(cues), "rushed_cues": rushed,
            "short_cues": sum(c["end"] - c["start"] < SHORT for c in cues),
            "overlapping_cues": sum(b["start"] < a["end"] - 0.01
                                    for a, b in pairwise(ordered)),
            "tail_seconds": round(last_word - last_cue, 2)}


def score(truth: Row, words: list[Row], cues: list[Row]) -> Row:
    """Against the truth to be subtitled; speech marked background counts only as extra."""
    import measures

    whole, truth = truth, measures.foreground(truth)
    truth_words = spoken(truth) if truth.get("sentences") else truth["words"]
    owned = owners(truth_words, cues)
    return {"truth_words": len(truth_words), "words": len(words),
            **word_timing(truth_words, words), **missing(truth_words, cues),
            **placement(truth_words, cues, owned),
            "duplicated_words": duplicated(truth_words, cues),
            **cue_shape(truth_words, cues),
            "speaker_accuracy": speaker_accuracy(truth_words, cues, owned),
            **measures.of_words(whole, words)}


def cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "ERR"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def table(rows: list[Row]) -> None:
    grid = [[head for _, head in TABLE]]
    grid += [[cell(row.get(key)) for key, _ in TABLE] for row in rows]
    widths = [max(len(r[i]) for r in grid) for i in range(len(TABLE))]
    for line in grid:
        print("  ".join(text.ljust(width) for text, width in zip(line, widths, strict=True)))
    for row in rows:
        if not row.get("ok"):
            print(f"ERROR {row.get('clip')} {row.get('fault')}: {row.get('error')}")


def main() -> None:
    if len(sys.argv) != 3:  # noqa: PLR2004
        raise SystemExit("score.py <run folder> <clip folder>")
    folder, clip = Path(sys.argv[1]), Path(sys.argv[2])
    kept = json.loads((folder / "score.json").read_text(encoding="utf-8"))
    truth = json.loads((clip / "truth.json").read_text(encoding="utf-8"))
    words = json.loads((folder / "words.json").read_text(encoding="utf-8"))
    cues = json.loads((folder / "cues.json").read_text(encoding="utf-8"))
    row = {**kept, **score(truth, words, cues)}
    print(json.dumps(row, indent=1))
    table([row])


if __name__ == "__main__":
    main()
