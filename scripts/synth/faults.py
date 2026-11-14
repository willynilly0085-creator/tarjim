"""What a cloud listener "heard", made from a synthetic clip's truth with faults put in on purpose.

The result is a heard.json in tarjim's own layout (tarjim/listen/merge.Heard, written by
tarjim/listen/kept.keep_heard): the clip cut into pieces the way tarjim cuts it
(listen/chunks.spans, about 75 s, cut in pauses), each piece with three passes at the piece's own
times, so kept.load_heard votes them again piece by piece exactly as a fresh hearing.

Faults are functions on a Draft, composed with "+" ("drift+omitted_one_pass") and seeded, so a
run is the same every time. Lines carry the truth sentences they came from ("ids") until export.
Truth marked "background" (speech in the sound nobody should subtitle) is never heard.
Since 2026-11-09 each piece after the first also carries the lead its request heard (leads.py).

`traced` also gives the regions each fault altered (faults.json beside the injected hearing):
{start, end, fault, kind, sentences}: kind "altered" for a truth sentence whose lines changed in
any pass (its truth span), "landed" where a moved or repeated copy of it fell outside that span,
"invented" for a line no truth sentence is behind.

    python faults.py <clip folder> <fault> <out folder> [--seed N]
"""
import argparse
import json
import random
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Any

import leads

from tarjim.listen.chunks import CHUNK_SECONDS, joined, spans
from tarjim.listen.coverage import merged
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard
from tarjim.listen.merge import PASSES, Heard, Piece

PROVIDER = "gemini"  # a cloud listener, so stretches left out are asked about again
JITTER = 0.3
DRIFT_AT_END = 6.0
DUPLICATE_LATER = 2.0
EARLY = 3.0
WRONG_SHARE = 0.1
SHORTEST = 0.05
SLIP, SLIP_SHARE = 60.0, 0.05  # an mm:ss misread: 1:05 heard as 2:05
MINUTE_PASSES = 2  # minute: the passes of the first piece written in minutes and seconds
TAIL_SHARE = 0.2  # omitted_tail: this share of a piece's speech, at its end
TAIL_PASSES = 2
LOOP_COPIES = 2  # loop_all: the line said again this many times, right after itself
LOOP_GAP = 0.15
INVENTED = "Thank you for watching, and do not forget to subscribe."
INVENTED_AFTER, INVENTED_LONG = 0.3, 3.0  # past the piece end; chunks.shift keeps it today

Line = dict[str, Any]  # start, end (clip times), speaker, text, ids


@dataclass
class Draft:
    truth: dict[str, Any]
    pieces: list[tuple[float, float]]
    passes: list[list[list[Line]]]  # [piece][pass][line]
    rng: random.Random
    regions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return float(self.truth["duration"])

    def every_pass(self) -> list[list[Line]]:
        return [run for piece in self.passes for run in piece]

    def ids(self) -> list[int]:
        return [i for i, s in enumerate(self.truth["sentences"]) if not s.get("background")]

    def pass_lines(self, n: int) -> list[Line]:
        return [x for piece in self.passes for x in piece[n]]

    def some(self, items: list[Any], share: float) -> list[Any]:
        """A seeded share of the items, at least one."""
        if not items:
            return []
        return self.rng.sample(items, max(1, round(share * len(items))))


def labels(sentences: list[dict[str, Any]]) -> dict[str, str]:
    """Truth speakers as a listener names them: S1, S2, ... by first appearance."""
    order: dict[str, str] = {}
    for sentence in sentences:
        if not sentence.get("background"):
            order.setdefault(sentence["speaker"], f"S{len(order) + 1}")
    return order


def piece_spans(truth: dict[str, Any]) -> list[tuple[float, float]]:
    speech = merged([(w["start"], w["end"]) for w in truth["words"]
                     if not w.get("background")], 0.0)
    return spans(float(truth["duration"]), speech, CHUNK_SECONDS)


def piece_of(middle: float, pieces: list[tuple[float, float]]) -> int:
    return next((i for i, (_, end) in enumerate(pieces) if middle < end), len(pieces) - 1)


def draft(truth: dict[str, Any], seed: int, name: str = "") -> Draft:
    pieces = piece_spans(truth)
    names = labels(truth["sentences"])
    passes: list[list[list[Line]]] = [[[] for _ in range(PASSES)] for _ in pieces]
    for index, s in enumerate(truth["sentences"]):
        if s.get("background"):
            continue
        line = {"start": float(s["start"]), "end": float(s["end"]),
                "speaker": names[s["speaker"]], "text": s["text"], "ids": [index]}
        for run in passes[piece_of((line["start"] + line["end"]) / 2, pieces)]:
            run.append(dict(line))
    return Draft(truth, pieces, passes, random.Random(f"{seed}:{truth.get('name')}:{name}"))


def perfect(_d: Draft) -> None:
    return None


def jitter(d: Draft) -> None:
    for run in d.every_pass():
        for line in run:
            line["start"] += d.rng.uniform(-JITTER, JITTER)
            line["end"] = max(line["end"] + d.rng.uniform(-JITTER, JITTER), line["start"] + 0.1)


def drift(d: Draft) -> None:
    """Late by k*t on the clip's timeline, never past the end of the sound the piece's listener
    was given: lines pile up at the piece's end, as a drifting listener's do."""
    k = DRIFT_AT_END / max(d.duration, 1.0)
    for (_, end), piece in zip(d.pieces, d.passes, strict=True):
        for line in (x for run in piece for x in run):
            line["start"] = min(line["start"] * (1 + k), end - 0.5)
            line["end"] = max(min(line["end"] * (1 + k), end), line["start"] + 0.3)


def stretched(d: Draft) -> None:
    for (_, end), piece in zip(d.pieces, d.passes, strict=True):
        for run in piece:
            if run:
                max(run, key=lambda x: x["start"])["end"] = end


def omitted_one_pass(d: Draft) -> None:
    for index in d.some(d.ids(), 0.15):
        out = d.rng.randrange(PASSES)
        for piece in d.passes:
            piece[out][:] = [x for x in piece[out] if index not in x["ids"]]


def omitted_all(d: Draft) -> None:
    gone = set(d.some(d.ids(), 0.1))
    for run in d.every_pass():
        run[:] = [x for x in run if not gone & set(x["ids"])]


def duplicated(d: Draft) -> None:
    lines = [(piece[0], x) for piece in d.passes for x in piece[0]]
    for run, line in d.some(lines, 0.1):
        run.append({**line, "start": line["start"] + DUPLICATE_LATER,
                    "end": line["end"] + DUPLICATE_LATER})


def merged_turns(d: Draft) -> None:
    sentences = d.truth["sentences"]
    pairs = [i for i in range(len(sentences) - 1)
             if sentences[i]["speaker"] != sentences[i + 1]["speaker"]]
    for first in d.some(pairs, 0.1):
        for run in d.every_pass():
            a = next((x for x in run if first in x["ids"]), None)
            b = next((x for x in run if first + 1 in x["ids"]), None)
            if a is None or b is None or a is b:
                continue
            a.update(end=max(a["end"], b["end"]), text=f"{a['text']} {b['text']}",
                     ids=[*a["ids"], *b["ids"]])
            run.remove(b)


def renumbered(run: list[Line], swap: bool) -> None:
    order: dict[str, str] = {}
    for line in sorted(run, key=lambda x: x["start"]):
        order.setdefault(line["speaker"], f"S{len(order) + 1}")
    if swap:
        order = {k: {"S1": "S2", "S2": "S1"}.get(v, v) for k, v in order.items()}
    for line in run:
        line["speaker"] = order[line["speaker"]]


def labels_swapped(d: Draft) -> None:
    """Speakers renumbered per request, S1/S2 swapped from a seeded piece on. A clip heard in
    one piece has its swap in one seeded pass instead (each pass is its own request, so it
    may name the speakers the other way round): swapping every pass alike changes nothing."""
    if len(d.pieces) > 1:
        start = d.rng.randrange(1, len(d.pieces))
        for index, piece in enumerate(d.passes):
            for run in piece:
                renumbered(run, index >= start)
        return
    odd = d.rng.randrange(PASSES)
    for number, run in enumerate(d.passes[0]):
        renumbered(run, number == odd)


def one_line(d: Draft) -> None:
    for (start, end), piece in zip(d.pieces, d.passes, strict=True):
        run = sorted(piece[0], key=lambda x: x["start"])
        if run:
            piece[0][:] = [{"start": start, "end": end, "speaker": run[0]["speaker"],
                            "text": " ".join(x["text"] for x in run),
                            "ids": [i for x in run for i in x["ids"]]}]


def wrong_words(d: Draft) -> None:
    vocabulary = sorted({w["text"] for w in d.truth["words"]})
    for run in d.every_pass():
        for line in run:
            words = line["text"].split()
            line["text"] = " ".join(
                d.rng.choice([v for v in vocabulary if v != w] or [w])
                if d.rng.random() < WRONG_SHARE else w for w in words)


def early(d: Draft) -> None:
    chosen = d.rng.randrange(len(d.pieces))
    for run in d.passes[chosen]:
        for line in run:
            line["start"] -= EARLY
            line["end"] -= EARLY


def slip(d: Draft) -> None:
    """An mm:ss misread: 5% of the lines a minute late, alike in every pass (one pass's misread
    is voted away); chunks.shift drops what lands past its piece."""
    chosen = set(d.some(d.ids(), SLIP_SHARE))
    for line in (x for run in d.every_pass() for x in run if chosen & set(x["ids"])):
        line["start"] += SLIP
        line["end"] += SLIP


def colonless(seconds: float) -> float:
    """A time as minutes and seconds with the colon left out: 69.12 s, 1:09.12, as 109.12."""
    return 100.0 * (seconds // 60) + seconds % 60


def minute(d: Draft) -> None:
    """Minutes and seconds with the colon left out, as a cloud listener was seen to write them
    (2026-11-14): the last two passes of the first piece give every time from its first minute
    on so, 1:09 as 109, and the pass before them is right. Their line said up to the minute runs
    to the start of the next, as that listener's lines did (each ended where the next began):
    its end is then past the minute too, which is what walled off every line after it. Only the
    first piece: a later one is read back at its request's times before it is kept
    (listen/lead.split). `slip` moves single lines a whole minute in every pass, which is not
    how it was seen to happen. The right pass heard one word fewer, as passes differ, so one
    written so is the fullest and the vote's base, as it was that day."""
    for line in d.passes[0][0][:1]:
        line["text"] = line["text"].rsplit(" ", 1)[0]
    for run in d.passes[0][-MINUTE_PASSES:]:
        run.sort(key=lambda x: x["start"])
        for line, after in pairwise(run):
            if line["end"] < SLIP <= after["start"]:
                line["end"] = after["start"]
        for line in run:
            line["start"], line["end"] = colonless(line["start"]), colonless(line["end"])


def two_labels(lines: list[Line]) -> tuple[str, str] | None:
    order: list[str] = []
    for line in sorted(lines, key=lambda x: x["start"]):
        if line["speaker"] not in order:
            order.append(line["speaker"])
    return (order[0], order[1]) if len(order) > 1 else None


def swapped_inside(d: Draft) -> None:
    """From a pause inside one piece on, its first two speakers swapped in every pass (the
    2026-11-06 case: the listener changed its mind about who is who half way through)."""
    chosen = [k for k, piece in enumerate(d.passes) if two_labels(piece[0])]
    if not chosen:
        return
    k = d.rng.choice(chosen)
    first, second = two_labels(d.passes[k][0]) or ("", "")
    lines = sorted(d.passes[k][0], key=lambda x: x["start"])
    pauses = [(a["end"] + b["start"]) / 2 for a, b in pairwise(lines) if b["start"] > a["end"]]
    inner = pauses[len(pauses) // 4: max(len(pauses) // 4 + 1, 3 * len(pauses) // 4)]
    cut = d.rng.choice(inner) if inner else lines[len(lines) // 2]["start"]
    swap = {first: second, second: first}
    for line in (x for run in d.passes[k] for x in run if x["start"] >= cut):
        line["speaker"] = swap.get(line["speaker"], line["speaker"])


def omitted_tail(d: Draft) -> None:
    """The last 20% of one piece's speech left out by two of its three passes."""
    chosen = [k for k, piece in enumerate(d.passes) if piece[0]]
    if not chosen:
        return
    k = d.rng.choice(chosen)
    first = min(x["start"] for x in d.passes[k][0])
    last = max(x["end"] for x in d.passes[k][0])
    cut = last - TAIL_SHARE * (last - first)
    for n in d.rng.sample(range(PASSES), TAIL_PASSES):
        run = d.passes[k][n]
        run[:] = [x for x in run if (x["start"] + x["end"]) / 2 < cut]


def labels_permuted(d: Draft) -> None:
    """Every pass of every piece names its speakers by its own seeded permutation, as separate
    requests may."""
    for run in d.every_pass():
        names = sorted({x["speaker"] for x in run})
        mapping = dict(zip(names, d.rng.sample(names, len(names)), strict=True))
        for line in run:
            line["speaker"] = mapping[line["speaker"]]


def loop_all(d: Draft) -> None:
    """A Gemini loop: one line said again LOOP_COPIES times right after itself, in every pass,
    so the vote keeps the copies (`duplicated` is pass 0 only, which the vote removes)."""
    lines = d.pass_lines(0)
    if not lines:
        return
    chosen = d.rng.choice(lines)["ids"]
    for run in d.every_pass():
        for line in [x for x in run if x["ids"] == chosen]:
            length, at = line["end"] - line["start"], line["end"]
            for _ in range(LOOP_COPIES):
                run.append({**line, "start": at + LOOP_GAP, "end": at + LOOP_GAP + length})
                at += LOOP_GAP + length


def tail_hallucination(d: Draft) -> None:
    """An invented line just past one piece's end, in every pass of it."""
    k = d.rng.randrange(len(d.pieces))
    end = d.pieces[k][1]
    last = max(d.passes[k][0], key=lambda x: x["start"], default=None)
    line = {"start": end + INVENTED_AFTER, "end": end + INVENTED_AFTER + INVENTED_LONG,
            "speaker": last["speaker"] if last else "S1", "text": INVENTED, "ids": []}
    for run in d.passes[k]:
        run.append(dict(line))


def piece_empty(d: Draft) -> None:
    """Every pass of one piece answered with nothing (the 178 s stop)."""
    chosen = [k for k, piece in enumerate(d.passes) if piece[0]] or [0]
    for run in d.passes[d.rng.choice(chosen)]:
        run.clear()


FAULTS: dict[str, Callable[[Draft], None]] = {
    "perfect": perfect, "jitter": jitter, "drift": drift, "stretched": stretched,
    "omitted_one_pass": omitted_one_pass, "omitted_all": omitted_all,
    "duplicated": duplicated, "merged": merged_turns, "labels_swapped": labels_swapped,
    "one_line": one_line, "wrong_words": wrong_words, "early": early, "slip": slip,
    "minute": minute,
    "swapped_inside": swapped_inside, "omitted_tail": omitted_tail,
    "labels_permuted": labels_permuted, "loop_all": loop_all,
    "tail_hallucination": tail_hallucination, "piece_empty": piece_empty}


def parts_of(fault: str) -> list[str]:
    names = [n for n in re.split(r"[+,]", fault) if n]
    unknown = [n for n in names if n not in FAULTS]
    if unknown or not names:
        raise ValueError(f"unknown fault(s) {unknown or fault!r}; known: {', '.join(FAULTS)}")
    return names


def local(line: Line, span: tuple[float, float]) -> Utterance:
    """A line at its piece's own times, as the listener of that piece answered it."""
    start = max(line["start"] - span[0], 0.0)  # past the piece: dropped by chunks.shift, as live
    end = max(line["end"] - span[0], start + SHORTEST)
    return Utterance(round(start, 3), round(end, 3), str(line["speaker"]), str(line["text"]))


def led(lead_s: float, lead: list[list[Line]], span: tuple[float, float]) -> dict[str, Any]:
    """A piece's lead as its Piece takes it: the lines at the times of its request."""
    heard_from = (span[0] - lead_s, span[1])
    return {"lead_s": lead_s, "lead": [[local(x, heard_from) for x in run] for run in lead]}


def to_heard(d: Draft) -> Heard:
    """The hearing; each piece after the first with its lead (leads.py) when tarjim takes one."""
    found = leads.leads(d.truth, d.pieces, d.passes, CHUNK_SECONDS) if leads.supported() else \
        [(0.0, [])] * len(d.pieces)
    pieces = [Piece(span[0], span[1], [[local(x, span) for x in sorted(run, key=lambda x:
                                                                           x["start"])]
                                       for run in piece], **(led(*lead, span) if lead[0] else {}))
              for span, piece, lead in zip(d.pieces, d.passes, found, strict=True)]
    utterances, passes = joined(pieces)
    return Heard(str(d.truth.get("language") or ""), utterances, passes, provider=PROVIDER,
                 pieces=pieces)


Seen = dict[int, list[tuple[float, float, str, str]]]


def seen(d: Draft) -> Seen:
    """Every line of every pass by the truth sentence behind it (-1: none)."""
    out: Seen = {}
    for line in (x for run in d.every_pass() for x in run):
        for i in line["ids"] or [-1]:
            out.setdefault(i, []).append((round(line["start"], 3), round(line["end"], 3),
                                          str(line["speaker"]), str(line["text"])))
    return {i: sorted(v) for i, v in out.items()}


def clipped(d: Draft, start: float, end: float) -> tuple[float, float] | None:
    low, high = max(0.0, start), min(d.duration, end)
    return (round(low, 3), round(high, 3)) if high > low else None


def region(span: tuple[float, float], fault: str, kind: str, ids: list[int]) -> dict[str, Any]:
    return {"start": span[0], "end": span[1], "fault": fault, "kind": kind, "sentences": ids}


def altered(d: Draft, before: Seen, after: Seen, fault: str) -> list[dict[str, Any]]:
    """The regions one fault changed: truth spans of sentences whose lines changed, where their
    new copies landed outside them, and lines invented from nothing."""
    out: list[dict[str, Any]] = []
    for i, s in enumerate(d.truth["sentences"]):
        if before.get(i, []) == after.get(i, []):
            continue
        a, b = float(s["start"]), float(s["end"])
        out.append(region((a, b), fault, "altered", [i]))
        for start, end, _, _ in Counter(after.get(i, [])) - Counter(before.get(i, [])):
            span = clipped(d, start, end)
            if span and (span[1] <= a or span[0] >= b):
                out.append(region(span, fault, "landed", [i]))
    for start, end, _, _ in Counter(after.get(-1, [])) - Counter(before.get(-1, [])):
        last = round(d.duration, 3)
        out.append(region(clipped(d, start, end) or (last, last), fault, "invented", []))
    return out


def traced(truth: dict[str, Any], fault: str, seed: int = 0) -> tuple[Heard, list[dict]]:
    """The hearing with the faults in, and the regions each fault altered."""
    d = draft(truth, seed, fault)
    for name in parts_of(fault):
        before = seen(d)
        FAULTS[name](d)
        d.regions += altered(d, before, seen(d), name)
    return to_heard(d), sorted(d.regions, key=lambda r: (r["start"], r["end"]))


def inject(truth: dict[str, Any], fault: str, seed: int = 0) -> Heard:
    return traced(truth, fault, seed)[0]


def regions(truth: dict[str, Any], fault: str, seed: int = 0) -> list[dict[str, Any]]:
    return traced(truth, fault, seed)[1]


def write_regions(folder: Path, found: list[dict[str, Any]]) -> None:
    (folder / "faults.json").write_text(json.dumps(found, indent=1), encoding="utf-8")


def write(truth: dict[str, Any], fault: str, cache: Path, seed: int = 0) -> Heard:
    """heard.json in `cache`, in the layout kept.load_heard reads, and faults.json beside it."""
    heard, found = traced(truth, fault, seed)
    cache.mkdir(parents=True, exist_ok=True)
    keep_heard(cache, heard)
    write_regions(cache, found)
    return heard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("clip", type=Path)
    parser.add_argument("fault")
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    truth = json.loads((args.clip / "truth.json").read_text(encoding="utf-8"))
    heard = write(truth, args.fault, args.out, args.seed)
    print(f"{args.out / 'heard.json'}: {len(heard.pieces)} piece(s), "
          f"{len(heard.utterances)} voted lines")


if __name__ == "__main__":
    main()
