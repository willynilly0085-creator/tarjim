"""Build the synthetic ground-truth clips: clip.wav, clip.mp4 and truth.json per scenario.

Usage: python make.py [scenario ...]   (default: every scenario in scenarios.py)
Data goes to C:\\Users\\PC\\Desktop\\tarjim-synth (override with TARJIM_SYNTH).

Background lines (a radio under a meeting) are mixed in under the dialogue and marked
"background" in truth.json. A scenario with `vad_below` (en_chant_bed) has its bed raised from
its bed_db until tarjim's voice detector (tarjim.asr.vad) hears less than that share of the truth
speech; make.py fails when no bed up to BED_MOST dB gets there, since the smoke tier needs it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import audio
import beds
import numpy as np
from scenarios import SCENARIOS, Line, Scenario, Voice, by_name

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("TARJIM_SYNTH", r"C:\Users\PC\Desktop\tarjim-files\tarjim-synth"))
TTS = ROOT / "work" / "tts"
PAD_BEFORE, PAD_AFTER = 0.02, 0.05
SENTENCE = re.compile(r"[^.?!؟]+[.?!؟]*")
ROOM_DB = -72.0  # faint room tone under every clip, so no stretch is digital silence
BED_STEP, BED_MOST = 1.0, 16.0


@dataclass
class Take:
    """One synthesized line, trimmed to its speech; times relative to `x`."""
    x: np.ndarray
    words: list[tuple[str, float, float, int]]  # text, start, end, char pos

    @property
    def first(self) -> float:
        return self.words[0][1]

    @property
    def last(self) -> float:
        return self.words[-1][2]


def take_key(voice: Voice, text: str) -> str:
    raw = f"{voice.base}|{voice.pitch}|{voice.rate}|{text}".encode()
    return hashlib.sha1(raw).hexdigest()[:16]


def synth_missing(pairs: list[tuple[Voice, str]]) -> None:
    jobs, seen = [], set()
    for voice, text in pairs:
        k = take_key(voice, text)
        if k in seen or (TTS / f"{k}.json").exists():
            continue
        seen.add(k)
        jobs.append({"voice": voice.base, "pitch": voice.pitch, "rate": voice.rate,
                     "text": text, "wav": str(TTS / f"{k}.wav"), "json": str(TTS / f"{k}.json")})
    if not jobs:
        return
    print(f"synthesizing {len(jobs)} lines ...", flush=True)
    jobfile = TTS / "jobs.json"
    jobfile.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(HERE / "tts.ps1"), "-Jobs", str(jobfile)], check=True)


def load_take(voice: Voice, text: str) -> Take:
    k = take_key(voice, text)
    wav = TTS / f"{k}.wav"
    raw = json.loads((TTS / f"{k}.json").read_text(encoding="utf-8-sig") or "[]")
    n_in = len(audio.read_wav(wav))
    if voice.shift != 1.0:
        shifted = TTS / f"{k}_s{voice.shift}.wav"
        if not shifted.exists():
            audio.shift_voice(wav, shifted, voice.shift)
        wav = shifted
    x = audio.read_wav(wav)
    scale = len(x) / n_in  # atempo keeps the duration; rescale by any tiny residue
    spans = audio.refine([w["start"] * scale for w in raw], x)
    words = [(w["text"], a, b, int(w["pos"])) for w, (a, b) in zip(raw, spans, strict=True)]
    return trim(x, words)


def trim(x: np.ndarray, words: list[tuple[str, float, float, int]]) -> Take:
    a = max(0.0, words[0][1] - PAD_BEFORE)
    b = min(len(x) / audio.SR, words[-1][2] + PAD_AFTER)
    cut = x[int(round(a * audio.SR)): int(round(b * audio.SR))]
    return Take(cut, [(t, s - a, e - a, p) for t, s, e, p in words])


def place(lines: list[Line], takes: list[Take], lead: float) -> list[float]:
    """Timeline time of each line's first word."""
    starts: list[float] = []
    ref = lead  # moment everyone placed so far has stopped talking
    for (_, _, gap, over), tk in zip(lines, takes, strict=True):
        start = ref + gap - (over if starts else 0.0)
        starts.append(start)
        ref = max(ref, start + tk.last - tk.first)
    return starts


@dataclass
class Layout:
    """The clip laid out: the dialogue, and the background lines that must not be subtitled."""
    takes: list[Take]
    starts: list[float]
    back_lines: list[Line]
    back: list[Take]
    back_starts: list[float]
    n: int


def layout(sc: Scenario) -> Layout:
    takes = [load_take(sc.voices[spk], text) for spk, text, _, _ in sc.lines]
    starts = place(sc.lines, takes, sc.lead_s)
    end = max(s + tk.last - tk.first for s, tk in zip(starts, takes, strict=True))
    back = [load_take(sc.voices[spk], text) for spk, text, _, _ in sc.background]
    back_starts = place(sc.background, back, sc.background_lead_s) if back else []
    kept = [i for i, (s, tk) in enumerate(zip(back_starts, back, strict=True))
            if s + tk.last - tk.first <= end]  # the radio stops when the meeting does
    return Layout(takes, starts, [sc.background[i] for i in kept], [back[i] for i in kept],
                  [back_starts[i] for i in kept], int(round((end + sc.tail_s) * audio.SR)))


def laid(takes: list[Take], starts: list[float], n: int) -> np.ndarray:
    y = np.zeros(n + audio.SR, np.float64)
    for s, tk in zip(starts, takes, strict=True):
        a = int(round((s - tk.first) * audio.SR))
        y[a: a + len(tk.x)] += tk.x
    return y[:n]


def active_rms(y: np.ndarray) -> float:
    frames = audio.frame_db(y.astype(np.float32))
    return float(10.0 ** (np.percentile(frames[frames > -40.0], 50) / 20.0))


def voices(sc: Scenario, lay: Layout) -> np.ndarray:
    y = laid(lay.takes, lay.starts, lay.n)
    if lay.back:
        b = laid(lay.back, lay.back_starts, lay.n)
        y = y + b * (active_rms(y) * 10.0 ** (sc.background_db / 20.0) / active_rms(b))
    return y


def finish(sc: Scenario, clean: np.ndarray, bed_db: float) -> np.ndarray:
    """The voices under the scenario's bed at bed_db, normalized, over the room tone."""
    y = clean.copy()
    if sc.bed != "none":
        b = beds.bed(sc.bed, len(y))
        y += b * (active_rms(clean) * 10.0 ** (bed_db / 20.0) / np.sqrt(np.mean(b**2)))
    y *= 0.9 / np.max(np.abs(y))
    room = beds.noise(len(y), seed=3)
    y += room * (10.0 ** (ROOM_DB / 20.0) / np.sqrt(np.mean(room**2)))
    return y.astype(np.float32)


def timed(lines: list[Line], takes: list[Take], starts: list[float], duration: float,
          background: bool) -> tuple[list[dict], list[dict]]:
    words, sentences = [], []
    flag = {"background": True} if background else {}
    for (spk, text, _, _), tk, s in zip(lines, takes, starts, strict=True):
        shift = s - tk.first
        spans = [(t, round(a + shift, 3), round(min(b + shift, duration), 3), p)
                 for t, a, b, p in tk.words]
        words += [{"text": t, "start": a, "end": b, "speaker": spk, **flag}
                  for t, a, b, _ in spans]
        for m in SENTENCE.finditer(text):
            inside = [w for w in spans if m.start() <= w[3] < m.end()]
            if inside and m.group().strip():
                sentences.append({"start": inside[0][1], "end": inside[-1][2],
                                  "speaker": spk, "text": m.group().strip(), **flag})
    return words, sentences


def truth(sc: Scenario, lay: Layout, duration: float) -> dict:
    words, sentences = timed(sc.lines, lay.takes, lay.starts, duration, False)
    if lay.back:
        more = timed(lay.back_lines, lay.back, lay.back_starts, duration, True)
        words, sentences = words + more[0], sentences + more[1]
    words.sort(key=lambda w: (w["start"], w["end"]))
    sentences.sort(key=lambda w: (w["start"], w["end"]))
    return {"name": sc.name, "language": sc.language, "duration": round(duration, 3),
            "words": words, "sentences": sentences}


def vad_recall(y: np.ndarray, words: list[dict]) -> float:
    """Share of the truth speech (10 ms frames) tarjim's voice detector calls speech."""
    sys.path.insert(0, str(HERE.parents[1]))
    from tarjim.asr.vad import speech_regions

    heard = np.zeros(len(y) // audio.HOP + 1, bool)
    for a, b in speech_regions(y):
        heard[int(a * 100): int(b * 100) + 1] = True
    said = np.zeros_like(heard)
    for w in words:
        if not w.get("background"):
            said[int(w["start"] * 100): int(w["end"] * 100)] = True
    return float((heard & said).sum() / max(1, said.sum()))


def under_bed(sc: Scenario, clean: np.ndarray, words: list[dict]) -> tuple[np.ndarray, dict]:
    """The clip with its bed. For a `vad_below` scenario the bed goes up from sc.bed_db in
    BED_STEP dB steps until the voice detector misses enough of the speech, or this fails."""
    bed_db = sc.bed_db
    while True:
        y = finish(sc, clean, bed_db)
        if sc.vad_below is None:
            return y, {}
        recall = vad_recall(y, words)
        print(f"  {sc.name}: bed {bed_db:+.0f} dB -> voice detector recall {recall:.3f}",
              flush=True)
        if recall < sc.vad_below:
            return y, {"bed_db": bed_db, "vad_recall": round(recall, 3)}
        if bed_db + BED_STEP > BED_MOST:
            raise SystemExit(f"{sc.name}: the voice detector still hears {recall:.2f} of the "
                             f"speech with the bed at {bed_db:+.0f} dB; need < {sc.vad_below}")
        bed_db += BED_STEP


def write_mp4(wav: Path, mp4: Path) -> None:
    subprocess.run([audio.FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=0x14171c:s=640x360:r=25", "-i", str(wav), "-map", "0:v",
                    "-map", "1:a", "-c:v", "libopenh264", "-b:v", "150k", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", str(mp4)], check=True)


def build(sc: Scenario) -> dict:
    lay = layout(sc)
    doc = truth(sc, lay, lay.n / audio.SR)
    y, measured = under_bed(sc, voices(sc, lay), doc["words"])
    doc.update(measured)
    out = ROOT / "clips" / sc.name
    out.mkdir(parents=True, exist_ok=True)
    audio.write_wav(out / "clip.wav", y)
    (out / "truth.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    write_mp4(out / "clip.wav", out / "clip.mp4")
    return doc


def main(names: list[str]) -> None:
    chosen = [by_name(n) for n in names] if names else SCENARIOS
    TTS.mkdir(parents=True, exist_ok=True)
    synth_missing([(sc.voices[spk], text) for sc in chosen
                   for spk, text, _, _ in [*sc.lines, *sc.background]])
    for sc in chosen:
        doc = build(sc)
        flag = "" if 60.0 <= doc["duration"] <= sc.longest_s else \
            f"  <-- outside 60-{sc.longest_s:.0f} s"
        bed = f"  bed {doc['bed_db']:+.0f} dB, VAD recall {doc['vad_recall']}" \
            if "vad_recall" in doc else ""
        back = sum(1 for w in doc["words"] if w.get("background"))
        print(f"{sc.name:24s} {sc.language:8s} {doc['duration']:7.2f}s "
              f"{len(doc['words']):4d} words {len(doc['sentences']):3d} sentences"
              f"{f' ({back} background)' if back else ''}{flag}{bed}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
