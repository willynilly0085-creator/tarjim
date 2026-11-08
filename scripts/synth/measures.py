"""More measures of a run, beside score.py's: from the words (`of_words`, called by score.score)
and from the run itself (`Probe`, around one cell in run.py).

From the words:
    slope           s/min, OLS slope of the signed start error against truth time
    extra_words     output words matched to no (foreground) truth word
    on_silence      output words whose middle is more than 0.3 s from any truth word
    background_words output words that are the background voice's (truth "background")
    flips           speaker changes inside one truth turn (consecutive same-speaker sentences)
From the run (null when the thing measured does not exist in this code):
    letters_passes  tarjim.asr.letters.Letters total delta: whole-clip MMS passes
    vad_runs        calls to tarjim.asr.vad.speech_regions, and vad_sites per call site
    cpu_s_per_min   process CPU seconds per minute of clip
    peak_mb         peak resident memory (psutil), null without psutil
    source_share    Counter of Word.source, null while Word has no source
    guards          tarjim.guards.counts(), null while tarjim.guards does not exist
    contract_*      from contract.json in the job folder, null when absent
    map_f1          speech.json's speech map against truth word spans +-0.1 s, null when absent
"""
import bisect
import contextlib
import importlib
import json
import statistics
import sys
import threading
import time
import weakref
from collections import Counter
from pathlib import Path
from typing import Any
from unittest import mock

Row = dict[str, Any]
SILENT = 0.3
MAP_SLACK = 0.1
MAP_FRAME = 0.01
SAMPLE_S = 0.1


def foreground(truth: Row) -> Row:
    """The truth without its background voice: what should be subtitled."""
    if not any(w.get("background") for w in truth["words"]):
        return truth
    return {**truth, "words": [w for w in truth["words"] if not w.get("background")],
            "sentences": [s for s in truth.get("sentences") or [] if not s.get("background")]}


def slope(truth_words: list[Row], words: list[Row], matched: list[tuple[int, int]]) -> Any:
    xs = [float(truth_words[a]["start"]) for a, _ in matched]
    ys = [float(words[b]["start"]) - float(truth_words[a]["start"]) for a, b in matched]
    if len(xs) < 3 or max(xs) - min(xs) < 1.0:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    return round(60.0 * sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / var, 4)


def on_silence(all_words: list[Row], words: list[Row]) -> int:
    spans = sorted((float(w["start"]), float(w["end"])) for w in all_words)
    starts = [a for a, _ in spans]
    reach: list[float] = []  # the furthest end among spans up to each index
    for _, b in spans:
        reach.append(max(b, reach[-1]) if reach else b)
    count = 0
    for w in words:
        middle = (float(w["start"]) + float(w["end"])) / 2
        k = bisect.bisect_right(starts, middle)
        before = middle - reach[k - 1] if k else float("inf")
        after = starts[k] - middle if k < len(starts) else float("inf")
        count += min(max(before, 0.0), after) > SILENT
    return count


def background_words(back: list[Row], words: list[Row], used: set[int]) -> int:
    """Words left over by the foreground match that match the background voice near its time."""
    import score

    if not back:
        return 0
    rest = [j for j in range(len(words)) if j not in used]
    found = score.pairs(back, [words[j] for j in rest])
    return sum(abs(float(back[a]["start"]) - float(words[rest[b]]["start"])) < 2.0
               for a, b in found)


def flips(truth: Row, truth_words: list[Row], words: list[Row],
          matched: list[tuple[int, int]]) -> int | None:
    import score

    sentences = truth.get("sentences") or []
    if not sentences or not matched:
        return None
    turn, number = [], 0
    for k, s in enumerate(sentences):
        number += k > 0 and s["speaker"] != sentences[k - 1]["speaker"]
        turn.append(number)
    home = dict(zip((id(w) for w in truth["words"]), score.sentence_of(truth), strict=True))
    last: dict[int, str] = {}
    count = 0
    for a, b in sorted(matched):
        t = turn[home[id(truth_words[a])]]
        name = score.label(str(words[b].get("speaker") or ""))
        count += t in last and last[t] != name
        last[t] = name
    return count


def of_words(truth: Row, words: list[Row]) -> Row:
    """The measures from the words, `truth` whole (background included)."""
    import score

    fore = foreground(truth)
    truth_words = score.spoken(fore) if fore.get("sentences") else fore["words"]
    matched = score.pairs(truth_words, words)
    back = [w for w in truth["words"] if w.get("background")]
    return {"slope": slope(truth_words, words, matched),
            "extra_words": len(words) - len(matched),
            "on_silence": on_silence(truth["words"], words),
            "background_words": background_words(back, words, {b for _, b in matched}),
            "flips": flips(fore, truth_words, words, matched)}


def optional(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


class Probe:
    """Around one cell: a fresh findings record and guard counts, then what the run used."""

    def __init__(self) -> None:
        self.sites: Counter[str] = Counter()
        self.letters: weakref.WeakSet[Any] = weakref.WeakSet()
        self.before: dict[int, int] = {}
        self.peak = 0.0
        self.stop = threading.Event()
        self.stack = contextlib.ExitStack()

    def __enter__(self) -> "Probe":
        found = optional("tarjim.findings")
        if found is not None and hasattr(found, "collecting"):
            found.collecting()
        guards = optional("tarjim.guards")
        if guards is not None and hasattr(guards, "reset"):
            guards.reset()
        self.watch_vad()
        self.watch_letters()
        self.watch_memory()
        self.cpu = time.process_time()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.cpu = time.process_time() - self.cpu
        self.stop.set()
        self.stack.close()

    def watch_vad(self) -> None:
        vad = optional("tarjim.asr.vad")
        real = getattr(vad, "speech_regions", None)
        if real is None:
            self.sites = None  # type: ignore[assignment]
            return

        def counted(*args: Any, **kwargs: Any) -> Any:
            caller = sys._getframe(1)
            self.sites[f"{caller.f_globals.get('__name__')}.{caller.f_code.co_name}"] += 1
            return real(*args, **kwargs)

        self.stack.enter_context(mock.patch.object(vad, "speech_regions", counted))

    def watch_letters(self) -> None:
        module = optional("tarjim.asr.letters")
        kind = getattr(module, "Letters", None)
        if kind is None:
            self.letters = None  # type: ignore[assignment]
            return
        align = optional("tarjim.asr.align")
        shared = getattr(align, "shared_aligner", None)
        if shared is not None and shared.cache_info().currsize:
            have = getattr(getattr(shared(), "emitter", None), "emissions", None)
            if isinstance(have, kind):
                # a new cell is a new job: the clip before is not kept, so whether this cell's
                # array happens to reuse the last one's id() cannot change the count
                if hasattr(have, "last"):
                    have.last = None
                self.letters.add(have)
                self.before[id(have)] = int(getattr(have, "total", 0))
        real = kind.__init__
        probe = self

        def made(letters: Any, *args: Any, **kwargs: Any) -> None:
            real(letters, *args, **kwargs)
            probe.letters.add(letters)

        self.stack.enter_context(mock.patch.object(kind, "__init__", made))

    def watch_memory(self) -> None:
        psutil = optional("psutil")
        if psutil is None:
            self.peak = None  # type: ignore[assignment]
            return
        me = psutil.Process()

        def sample() -> None:
            while not self.stop.is_set():
                self.peak = max(self.peak, me.memory_info().rss / 2**20)
                self.stop.wait(SAMPLE_S)

        threading.Thread(target=sample, daemon=True).start()

    def passes(self) -> int | None:
        if self.letters is None:
            return None
        return sum(int(getattr(x, "total", 0)) - self.before.get(id(x), 0) for x in self.letters)

    def results(self, folder: Path, truth: Row, words: list[Row]) -> Row:
        minutes = max(float(truth["duration"]) / 60.0, 1e-6)
        guards = optional("tarjim.guards")
        counts = getattr(guards, "counts", None)
        sources = [w["source"] for w in words if "source" in w]
        return {"letters_passes": self.passes(),
                "vad_runs": None if self.sites is None else sum(self.sites.values()),
                "vad_sites": None if self.sites is None else dict(self.sites),
                "cpu_s_per_min": round(self.cpu / minutes, 2),
                "peak_mb": None if self.peak is None else round(self.peak, 1),
                "source_share": dict(Counter(sources)) if sources else None,
                "guards": dict(counts()) if callable(counts) else None,
                **contract(folder), "map_f1": map_f1(folder, truth)}


CONTRACT_FIELDS = ("contract_recall", "silent_fail", "false_alarm_per_10min")


def overlaps(a: Row, b: Row) -> bool:
    return float(a["start"]) < float(b["end"]) and float(b["start"]) < float(a["end"])


def contract(folder: Path) -> Row:
    """contract.json's own fields when it has them, else recall and false alarms of its flagged
    regions against faults.json; all null without a contract.json."""
    path = folder / "contract.json"
    if not path.exists():
        return dict.fromkeys(CONTRACT_FIELDS)
    data = json.loads(path.read_text(encoding="utf-8"))
    if all(k in data for k in CONTRACT_FIELDS):
        return {k: data[k] for k in CONTRACT_FIELDS}
    flagged = [r for r in data.get("regions") or [] if r.get("verdict", "off") != "ok"]
    faults = json.loads((folder / "faults.json").read_text(encoding="utf-8")) \
        if (folder / "faults.json").exists() else []
    hit = sum(any(overlaps(f, r) for r in flagged) for f in faults)
    false = sum(not any(overlaps(r, f) for f in faults) for r in flagged)
    minutes = max(float(data.get("duration") or 600.0) / 60.0, 1e-6)
    return {"contract_recall": round(hit / len(faults), 3) if faults else None,
            "silent_fail": int(bool(faults) and not flagged),
            "false_alarm_per_10min": round(10.0 * false / minutes, 2)}


def spans_in(data: Any) -> list[tuple[float, float]]:
    rows = data.get("regions") or data.get("map") or data.get("speech") or [] \
        if isinstance(data, dict) else data
    out = []
    for r in rows:
        if isinstance(r, dict) and r.get("speech", True) is not False:
            out.append((float(r["start"]), float(r["end"])))
        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((float(r[0]), float(r[1])))
    return out


def map_f1(folder: Path, truth: Row) -> float | None:
    path = folder / "speech.json"
    if not path.exists():
        return None
    said = spans_in(json.loads(path.read_text(encoding="utf-8")))
    real = [(float(w["start"]), float(w["end"])) for w in foreground(truth)["words"]]
    n = int(float(truth["duration"]) / MAP_FRAME) + 1

    def mask(spans: list[tuple[float, float]], pad: float) -> list[bool]:
        out = [False] * n
        for a, b in spans:
            for k in range(max(0, int((a - pad) / MAP_FRAME)), min(n, int((b + pad) / MAP_FRAME))):
                out[k] = True
        return out

    got, want = mask(said, 0.0), mask(real, 0.0)
    near_want, near_got = mask(real, MAP_SLACK), mask(said, MAP_SLACK)
    precision = sum(g and w for g, w in zip(got, near_want, strict=True)) / max(1, sum(got))
    recall = sum(w and g for w, g in zip(want, near_got, strict=True)) / max(1, sum(want))
    return round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0
