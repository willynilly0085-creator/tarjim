"""The decode bench: the strict aligner (asr/ctc.token_spans) and the tolerant one
(asr/tolerant.py) on the bench clips' whole-clip letters, with faults put in the text
(decode_text.py), each word's start against its true start (2026-11-08).

    python decode_bench.py [--label L] [--clips a,b] [--faults perfect,extra,missing,duplicated]
                           [--letters none|sparse|wrong] [--seed N] [--no-vad] [--cpu]
                           [--skip-base X] [--skip-per-token Y]

The letters are read from the timing bench's decode cache (work/emissions, by clip name in its
index) or, for a clip not there, heard once and kept in work/decode_bench. The lines are searched
as asr/align.py does: in groups, each line's letters within a margin of its time, a group that
cannot be read cut at its quietest point. Three decoders: strict; star (the clip's calibrated
prices, asr/costs.py); star+skip. Per clip and fault: the median and p95 start error of the words
said, the same next to a line left out, the share of said words left out (present_skip) and of
words not said that were left out (absent_skip), the star's stretches, and the decoding time.
Each clip's calibration (runs found, letter frames, the spread, the star's delta) is written too.
results/decode-<label>.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SYNTH = Path(os.environ.get("TARJIM_SYNTH", r"C:\Users\PC\Desktop\tarjim-files\tarjim-synth"))
TOOLS = Path(r"C:\Users\PC\.tarjim\tools\ffmpeg\368ccdd16812dd8b"
             r"\ffmpeg-n8.1-latest-win64-lgpl-shared-8.1\bin")
for _key, _value in {"HF_HOME": str(REPO / ".models"), "TARJIM_HOME": str(SYNTH / "home"),
                     "TARJIM_FFMPEG": str(TOOLS / "ffmpeg.exe"),
                     "TARJIM_FFPROBE": str(TOOLS / "ffprobe.exe")}.items():
    os.environ.setdefault(_key, _value)
sys.path[:0] = [str(HERE), str(REPO)]
if "--cpu" in sys.argv:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import decode_ears  # noqa: E402
import decode_score  # noqa: E402
import decode_text  # noqa: E402
import numpy as np  # noqa: E402

from tarjim.asr import costs as pricing  # noqa: E402
from tarjim.asr.align import overlapping  # noqa: E402
from tarjim.asr.ctc import FRAME, token_spans  # noqa: E402
from tarjim.asr.groups import chunks, quietest, windows  # noqa: E402
from tarjim.asr.tolerant import Text, tolerant_spans  # noqa: E402
from tarjim.asr.vad import mute_silence, speech_mask  # noqa: E402

PAD = 2.0  # as asr/align.PAD
NO_LETTERS = decode_score.NO_LETTERS
Starts = decode_score.Starts


class Decoder:
    """One way of reading a group's letters: each word's start, or None for a group that cannot
    be read; it adds up the star's stretches and its own time."""

    def __init__(self, name: str, costs: pricing.Costs | None) -> None:
        self.name, self.costs = name, costs
        self.absorbed: list[float] = []
        self.seconds = 0.0

    def __call__(self, logp: np.ndarray, text: Text) -> Starts | None:
        began = time.process_time()
        try:
            return self.read(logp, text)
        finally:
            self.seconds += time.process_time() - began

    def read(self, logp: np.ndarray, text: Text) -> Starts | None:
        if self.costs is None:
            spans = token_spans(logp, text.tokens, text.bounds)
            if spans is None:
                return None
            placed = [True] * text.words
        else:
            found = tolerant_spans(logp, text, self.costs)
            if not any(found.placed):
                return None
            spans, placed = found.spans, found.placed
            self.absorbed += [b - a for a, b in found.absorbed]
        first: Starts = [None] * text.words
        for k, span in enumerate(spans):
            w = text.word_of[k]
            if span is not None and placed[w] and first[w] is None:
                first[w] = span[0]
        return first


class Cell:
    """One clip's letters, speech and lines, read by one decoder."""

    def __init__(self, logp: np.ndarray, speech: np.ndarray, ears: Any) -> None:
        self.logp, self.speech, self.ears = logp, speech, ears

    def text(self, lines: list[decode_text.Line], low: int) -> tuple[Text, list[tuple[int, int]]]:
        """The group's letters, each word's and each line's window; the (line, word) of each
        word that has letters."""
        owners, word_of, tokens, slots = [], [], [], []
        for li, line in enumerate(lines):
            for wi, said in enumerate(self.ears.said(line.words)):
                found = self.ears.tokens(said)
                slots += [(li, wi)] if found else []
                tokens += found
                word_of += [len(slots) - 1] * len(found)
                owners += [line] * len(found)
        return Text(tokens, word_of, windows(owners, low)), slots  # type: ignore[arg-type]

    def group(self, lines: list[decode_text.Line], decoder: Decoder) -> list[Starts]:
        low = max(0, int((lines[0].start - PAD) / FRAME))
        high = min(len(self.logp), int((max(x.end for x in lines) + PAD) / FRAME))
        text, slots = self.text(lines, low)
        enough = text.tokens and high - low >= len(text.tokens)
        starts = decoder(self.logp[low:high], text) if enough else None
        if starts is None and len(lines) > 1:
            return self.split(lines, decoder)
        out: list[Starts] = [[NO_LETTERS] * len(x.words) for x in lines]
        for k, (li, wi) in enumerate(slots):
            start = None if starts is None else starts[k]
            out[li][wi] = None if start is None else start + low * FRAME
        return out

    def split(self, lines: list[decode_text.Line], decoder: Decoder) -> list[Starts]:
        cut = quietest(lines, self.speech)  # type: ignore[arg-type]
        return self.group(lines[:cut], decoder) + self.group(lines[cut:], decoder)

    def read(self, lines: list[decode_text.Line], decoder: Decoder) -> list[Starts]:
        """As AlignEngine.align: a short reply said over a turn searched on its own."""
        over = overlapping(lines)  # type: ignore[arg-type]
        turns = [line for line, said_over in zip(lines, over, strict=True) if not said_over]
        timed: list[Starts] = []
        for group in chunks(turns):  # type: ignore[arg-type]
            timed += self.group(group, decoder)  # type: ignore[arg-type]
        found, rest = [], iter(timed)
        for line, said_over in zip(lines, over, strict=True):
            found += self.group([line], decoder) if said_over else [next(rest)]
        return found


def clip_rows(folder: Path, args: argparse.Namespace, ears: Any, pool: list) -> list[dict]:
    truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    ears.language, raw = truth["language"], ears.emissions(folder, truth)
    regions = [] if args.no_vad else ears.regions(folder)
    gaps = decode_score.calibration(raw, truth, ears)
    delta = pricing.delta_of(gaps)
    rows = [{"clip": folder.name, "fault": "calibration", "runs": gaps.runs,
             "frames": gaps.frames, "spread": gaps.spread, "unexplained": gaps.unexplained,
             "star_delta": delta}]
    for fault in args.faults:
        lines = decode_text.faulted(decode_text.lines_of(truth), fault, pool, args.seed)
        speech = speech_mask([*regions, *[(x.start, x.end) for x in lines]], len(raw))
        cell = Cell(raw if args.no_vad else mute_silence(raw, speech), speech, ears)
        costs = None if delta is None else pricing.Costs(delta)
        strict = None
        for decoder in (Decoder("strict", None), Decoder("star", costs),
                        Decoder("star+skip", None if costs is None else
                                pricing.Costs(delta, skip=True, skip_base=args.skip_base,
                                              skip_per_token=args.skip_per_token))):
            row = decode_score.scored(truth, lines, cell.read(lines, decoder))
            errors = row.pop("_errors")
            strict = errors if strict is None else strict
            same = [abs(errors[k] - strict[k]) <= FRAME + 1e-6 for k in errors if k in strict]
            rows.append({"clip": folder.name, "fault": fault, "decoder": decoder.name, **row,
                         "same_as_strict": round(float(np.mean(same)), 4) if same else None,
                         "absorbed_s": round(sum(decoder.absorbed), 2),
                         "absorbed_n": len(decoder.absorbed),
                         "cpu_s": round(decoder.seconds, 3), "star_delta": delta})
            print(json.dumps(rows[-1]), flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="dev")
    parser.add_argument("--clips", default="")
    parser.add_argument("--faults", default=",".join(decode_text.FAULTS))
    parser.add_argument("--letters", default="none", choices=["none", "sparse", "wrong"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-base", type=float, default=pricing.SKIP_BASE)
    parser.add_argument("--skip-per-token", type=float, default=pricing.SKIP_PER_TOKEN)
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    args.faults = args.faults.split(",")
    every = sorted(p for p in (SYNTH / "clips").iterdir() if (p / "truth.json").exists())
    folders = [p for p in every if not args.clips or p.name in args.clips.split(",")]
    ears = decode_ears.Ears(SYNTH, args.letters, args.seed)
    rows = []
    for folder in folders:
        pool = decode_ears.pool(every, folder)
        rows += clip_rows(folder, args, ears, pool)
        out = SYNTH / "results" / f"decode-{args.label}.json"
        out.write_text(json.dumps({"args": vars(args), "rows": rows}, indent=1),
                       encoding="utf-8")


if __name__ == "__main__":
    main()
