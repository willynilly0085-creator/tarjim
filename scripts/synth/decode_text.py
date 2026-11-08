"""The text the decode bench (decode_bench.py) gives the aligner: a clip's true lines, each word
knowing the true word it stands for, with one kind of fault put in (2026-11-08):

    perfect     the lines as said
    extra       lines from another clip in the same language put between two lines, about 5% of
                the words: text the sound does not hold
    missing     lines left out, about 20% of the words: sound the text does not hold
    duplicated  lines given twice, about 5% of the words: the second copy is not in the sound

Each line's times are moved by up to JITTER seconds, as a listener's are.
"""
import random
from dataclasses import dataclass, field, replace
from typing import Any

JITTER = 0.3
SHARES = {"extra": 0.05, "missing": 0.2, "duplicated": 0.05}
FAULTS = ("perfect", "extra", "missing", "duplicated")
Truth = dict[str, Any]


@dataclass(frozen=True)
class Line:
    start: float
    end: float
    speaker: str
    words: list[str]
    truth: list[int | None]  # the true word each stands for; None for an invented one
    kind: str = "said"  # "said" | "invented" | "copy"
    near: bool = False  # next to a line that was left out
    text: str = field(default="", compare=False)


def lines_of(truth: Truth) -> list[Line]:
    """The truth's sentences as lines, each with its words (by speaker and time); a background
    voice (a radio under the talk) is not written down, as a listener would leave it out."""
    words = truth["words"]
    lines = []
    said = [s for s in truth["sentences"] if not s.get("background")]
    for s in sorted(said, key=lambda s: s["start"]):
        mine = [k for k, w in enumerate(words) if w["speaker"] == s["speaker"]
                and s["start"] - 0.05 <= (w["start"] + w["end"]) / 2 <= s["end"] + 0.05]
        lines.append(Line(s["start"], s["end"], s["speaker"], [words[k]["text"] for k in mine],
                          list(mine), text=s["text"]))
    return lines


def jittered(lines: list[Line], rng: random.Random) -> list[Line]:
    return [replace(line, start=max(0.0, line.start + rng.uniform(-JITTER, JITTER)),
                    end=line.end + rng.uniform(-JITTER, JITTER)) for line in lines]


def chosen(lines: list[Line], share: float, rng: random.Random) -> set[int]:
    """Lines picked at random until they hold `share` of the words (at least one line)."""
    order = list(range(len(lines)))
    rng.shuffle(order)
    total, picked, held = sum(len(line.words) for line in lines), set(), 0
    for k in order:
        if picked and held >= share * total:
            break
        picked.add(k)
        held += len(lines[k].words)
    return picked


def invented(line: Line, pool: list[Line], rng: random.Random) -> Line:
    other = rng.choice(pool)
    seconds = max(1.0, 0.3 * len(other.words))
    return Line(line.end, line.end + seconds, line.speaker, list(other.words),
                [None] * len(other.words), "invented", text=other.text)


def faulted(lines: list[Line], fault: str, pool: list[Line], seed: int) -> list[Line]:
    rng = random.Random(f"{seed}:{fault}")
    if fault == "perfect":
        return jittered(lines, rng)
    picked = chosen(lines, SHARES[fault], rng)
    out: list[Line] = []
    for k, line in enumerate(lines):
        if fault == "missing" and k in picked:
            continue
        near = fault == "missing" and bool({k - 1, k + 1} & picked)
        out.append(replace(line, near=near))
        if fault == "duplicated" and k in picked:
            out.append(replace(line, kind="copy"))
        if fault == "extra" and k in picked and pool:
            out.append(invented(line, pool, rng))
    return jittered(out, rng)
