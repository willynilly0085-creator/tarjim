"""How the decode bench (decode_bench.py) scores one reading against the truth (2026-11-08):
per true word the best start among its copies, its error against the true start, and the shares
of words said and not said that were left out; and what calibrating the clip finds."""
import math
from typing import Any

import decode_text
import numpy as np

from tarjim.asr import costs as pricing
from tarjim.asr.agree import SLACK, runs
from tarjim.asr.ctc import FRAME
from tarjim.models import Word

OVER = 0.5  # seconds off that a viewer sees
NO_LETTERS = math.nan  # the start given to a word with no letters to find
Starts = list[float | None]


def pct(values: list[float], q: float) -> float | None:
    return round(float(np.percentile(values, q)), 3) if values else None


def copies(lines: list[decode_text.Line], starts: list[Starts],
           ) -> tuple[dict[int, list[float | None]], int, int, set[int]]:
    """Each true word's starts (one a copy), the words not said and how many of them were
    left out, and the true words next to a line left out."""
    best: dict[int, list[float | None]] = {}
    absent, absent_skipped, near = 0, 0, set()
    for line, found in zip(lines, starts, strict=True):
        for ti, start in zip(line.truth, found, strict=True):
            if start is not None and math.isnan(start):
                continue  # a word with no letters is not the aligner's to place
            absent += ti is None or line.kind == "copy"
            if ti is None:
                absent_skipped += start is None
                continue
            best.setdefault(ti, []).append(start)
            near |= {ti} if line.near else set()
    return best, absent, absent_skipped, near


def scored(truth: dict[str, Any], lines: list[decode_text.Line], starts: list[Starts]) -> dict:
    """Per true word, the best start among its copies; the left-out shares."""
    best, absent, absent_skipped, near = copies(lines, starts)
    errors, errs_near, skipped = {}, [], 0
    for ti, given in best.items():
        placed = [s for s in given if s is not None]
        skipped += not placed
        absent_skipped += min(len(given) - 1, len(given) - len(placed))
        if placed:
            errors[ti] = min(abs(s - truth["words"][ti]["start"]) for s in placed)
            errs_near += [errors[ti]] if ti in near else []
    values = list(errors.values())
    return {"words": len(best), "start_median": pct(values, 50), "start_p95": pct(values, 95),
            "over_0_5": round(float(np.mean(np.array(values) > OVER)), 4) if values else None,
            "near_median": pct(errs_near, 50), "near_p95": pct(errs_near, 95),
            "present_skip": round(skipped / max(1, len(best)), 4),
            "absent_skip": round(absent_skipped / absent, 4) if absent else None,
            "_errors": errors}


def calibration(logp: np.ndarray, truth: dict[str, Any], ears: Any) -> pricing.Gaps:
    """Measured on the runs of the words written down, at their true times: what the strict
    check would find of a good timing."""
    kept = [k for line in decode_text.lines_of(truth) for k in line.truth if k is not None]
    words = [Word(w["text"], w["start"], w["end"], w["speaker"])
             for w in (truth["words"][k] for k in kept)]
    found = []
    for run in runs(sorted(words, key=lambda w: w.start)):
        tokens = [t for w in run for t in ears.tokens(w.text)]
        low = max(0, int((run[0].start - SLACK) / FRAME))
        found.append(pricing.Run(tokens, low, min(len(logp), int((run[-1].end + SLACK) / FRAME)
                                                  + 1)))
    return pricing.measured(logp, found)
