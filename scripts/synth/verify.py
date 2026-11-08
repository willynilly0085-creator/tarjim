"""Check truth.json word times against the audio: cut words, gaps and word edges with
ffmpeg by their truth times and compare RMS energy.

Usage: python verify.py clip_name [clip_name ...]
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
from audio import FFMPEG, SR, rms_db
from make import ROOT
from scenarios import by_name


def cut(wav: str, start: float, end: float) -> np.ndarray:
    out = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                          "-i", wav, "-f", "s16le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0


def gaps(words: list[dict], least: float) -> list[tuple[float, float]]:
    """Stretches where nobody is talking, at least `least` seconds long."""
    out, reach = [], 0.0
    for w in sorted(words, key=lambda w: w["start"]):
        if w["start"] - reach >= least and reach > 0:
            out.append((reach, w["start"]))
        reach = max(reach, w["end"])
    return out


def spread(items: list, k: int = 3) -> list:
    if len(items) <= k:
        return items
    return [items[int(len(items) * (i + 1) / (k + 1))] for i in range(k)]


def check(name: str) -> bool:
    bed = by_name(name).bed
    folder = ROOT / "clips" / name
    doc = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    wav, words = str(folder / "clip.wav"), doc["words"]
    print(f"\n== {name} ({doc['language']}, {doc['duration']} s, {len(words)} words)")
    long_words = [w for w in words if w["end"] - w["start"] >= 0.3]
    w_db = [(w, rms_db(cut(wav, w["start"], w["end"]))) for w in spread(long_words)]
    g_db = [(g, rms_db(cut(wav, g[0] + 0.05, g[1] - 0.05))) for g in spread(gaps(words, 0.4))]
    for w, d in w_db:
        print(f"  word  {w['text']!r:16} {w['start']:8.3f}-{w['end']:8.3f}  {d:6.1f} dB")
    for g, d in g_db:
        print(f"  gap   {'':16} {g[0]:8.3f}-{g[1]:8.3f}  {d:6.1f} dB")
    margin = min(d for _, d in w_db) - max(d for _, d in g_db)
    ons, offs = edge_checks(wav, words)
    ok = margin >= 10.0 and all(ons) and all(offs)
    verdict = ("PASS" if ok else "FAIL") if bed == "none" else "INFO (under a bed)"
    print(f"  quietest word is {margin:.1f} dB over the loudest gap (need 10); onsets"
          f" {sum(ons)}/{len(ons)} ok; offsets {sum(offs)}/{len(offs)} ok  -> {verdict}")
    return ok or bed != "none"


def edge_checks(wav: str, words: list[dict]) -> tuple[list[bool], list[bool]]:
    """3 word onsets and 3 word offsets that border silence: 40 ms just outside the word
    (10 ms guard) must sit 20 dB under the word's own RMS; at an onset the 40 ms just
    inside must also jump 10 dB over the outside (word tails fade, so offsets only need
    to be louder inside than outside)."""
    by_start = sorted(words, key=lambda w: w["start"])
    g = gaps(words, 0.25)
    after, before = {round(b, 3) for _, b in g}, {round(a, 3) for a, _ in g}
    onsets = spread([w for w in by_start if round(w["start"], 3) in after])
    offsets = spread([w for w in by_start if round(w["end"], 3) in before])
    return [edge(wav, w, True) for w in onsets], [edge(wav, w, False) for w in offsets]


def edge(wav: str, w: dict, onset: bool) -> bool:
    t = w["start"] if onset else w["end"]
    sign = 1.0 if onset else -1.0
    inside = rms_db(cut(wav, *sorted((t + sign * 0.01, t + sign * 0.05))))
    outside = rms_db(cut(wav, *sorted((t - sign * 0.05, t - sign * 0.01))))
    word = rms_db(cut(wav, w["start"], w["end"]))
    ok = word - outside >= 20.0 and inside - outside >= (10.0 if onset else 0.0)
    print(f"  {'onset ' if onset else 'offset'} {w['text']!r:15} {t:8.3f}  word {word:6.1f} dB"
          f"  inside {inside:6.1f} dB  outside {outside:6.1f} dB  {'ok' if ok else 'BAD'}")
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Arabic words on a cp1252 console
    results = [check(n) for n in sys.argv[1:]]
    sys.exit(0 if all(results) else 1)
