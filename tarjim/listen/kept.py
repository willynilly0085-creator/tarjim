"""The hearing kept beside a clip's other work, so a re-run does not pay to listen again, with the
stretches asked about again and the transcript made from it. "Listen again" forgets them all.

Since 2026-11-08 a hearing that left speech out is kept too: before, one stretch nothing could fill
made every later run pay to listen to the whole clip again, and a computer without the local
listener listened again forever. Now only the stretches left out are asked about again, each at
most TRIES times across runs (listen/repair.py). The transcript carries a key made from the code
and the settings it was derived with; another key means it is derived again from the kept hearing,
with no new listening, so a fix reaches a clip done before it.
"""
import functools
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from tarjim.asr.base import Transcript
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, agreed
from tarjim.models import Word

HEARD = "heard.json"
ASKED = "asked.json"
TRANSCRIPT = "transcript.json"
MADE_FROM_IT = "cues.*.json"
DERIVE = "derive"
TRIES = 2  # times a stretch is answered when asked about again, across runs
SAME = 0.5  # share of the shorter of two stretches they share: the same stretch
PAD = 0.75  # seconds of sound either side of a stretch, so its first and last words are whole
ROOT = Path(__file__).resolve().parent.parent
DERIVED_FROM = ("listen", "asr", "segment.py", "dialogue.py", "model_pins.py", "hearing.py")

Span = tuple[float, float]
Relisten = Callable[[float, float], list[Utterance]]  # what is said in a stretch, in clip times


class Spent(Exception):
    """The stretch was asked about TRIES times already: it is not asked again."""


def load_heard(cache: Path) -> Heard | None:
    kept = cache / HEARD
    if not kept.exists():
        return None
    data = json.loads(kept.read_text(encoding="utf-8"))
    words = data.get("local_words")
    passes = [[Utterance(**u) for u in run] for run in data.get("passes") or []]
    voted = agreed(passes) if passes else [Utterance(**u) for u in data["utterances"]]
    return Heard(data["language"], voted, passes,
                 None if words is None else [Word(**w) for w in words],
                 str(data.get("provider") or ""),
                 [Utterance(**u) for u in data.get("added") or []])


def keep_heard(cache: Path, heard: Heard) -> None:
    (cache / HEARD).write_text(json.dumps(asdict(heard), ensure_ascii=False, indent=1),
                               encoding="utf-8")


def same(span: Sequence[float], start: float, end: float) -> bool:
    shared = min(span[1], end) - max(span[0], start)
    return shared >= SAME * min(span[1] - span[0], end - start)


def inside(line: Utterance, start: float, end: float) -> Utterance:
    return replace(line, start=max(line.start, start), end=min(line.end, end))


def heard_span(start: float, end: float) -> Span:
    """The sound asked about for a stretch: the stretch and PAD either side."""
    return max(0.0, start - PAD), end + PAD


@dataclass
class Asked:
    """Each stretch asked about again. Within a job, what was heard: a stretch inside sound heard
    already is answered from it, never paid for again (2026-11-08: the second timing asked Gemini
    about the same gaps again, up to six requests a gap). Across runs, how often it was answered:
    a request that failed is no try, or two busy hours gave the speech up for good (2026-11-08)."""
    path: Path
    tries: list[list[float]]  # [start, end, times answered]
    answers: list[tuple[Span, list[Utterance]]] = field(default_factory=list)
    counted: list[Span] = field(default_factory=list)  # counted in this job

    @classmethod
    def load(cls, cache: Path) -> "Asked":
        try:
            data = json.loads((cache / ASKED).read_text(encoding="utf-8"))
            tries = [[float(a), float(b), int(n)] for a, b, n in data["asked"]]
        except (OSError, ValueError, KeyError, TypeError):
            tries = []
        return cls(cache / ASKED, tries)

    def save(self) -> None:
        self.path.write_text(json.dumps({"asked": self.tries}), encoding="utf-8")

    def known(self, start: float, end: float) -> list[Utterance] | None:
        """The lines of sound heard already that holds the whole stretch, within the sound this
        stretch asks about. Until 2026-11-08 the sound asked for was compared, so a gap moved by a
        tenth of a second, as between the two timings, was paid for again."""
        low, high = heard_span(start, end)
        for (first, last), lines in self.answers:
            if first <= start and end <= last:
                return [inside(u, low, high) for u in lines if low <= (u.start + u.end) / 2 <= high]
        return None

    def entry(self, span: Span) -> list[float] | None:
        return next((t for t in self.tries if same(t, *span)), None)

    def this_job(self, span: Span) -> bool:
        return any(same(c, *span) for c in self.counted)

    def allow(self, span: Span) -> None:
        entry = self.entry(span)
        if entry is not None and entry[2] >= TRIES and not self.this_job(span):
            raise Spent(f"{span[0]:.1f}-{span[1]:.1f} s was answered {TRIES} times")

    def count(self, span: Span) -> None:
        """One try for an answered stretch, once a job: more sound beside a stretch asked in this
        job is the same stretch, not another try."""
        if self.this_job(span):
            return
        self.counted.append(span)
        entry = self.entry(span)
        if entry is None:
            self.tries.append([*span, 1])
        else:
            entry[2] += 1

    def asking(self, relisten: Relisten) -> Relisten:
        """`relisten` asked about a stretch's sound (heard_span), through this record."""
        def once(start: float, end: float) -> list[Utterance]:
            known = self.known(start, end)
            if known is not None:
                return known
            span = heard_span(start, end)
            self.allow(span)
            lines: list[Utterance] = []
            try:  # a failed request is answered with nothing for the rest of the job
                lines = relisten(*span)
                self.count(span)
            finally:
                self.answers.append((span, lines))
            return lines

        return once


def sources(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


@functools.cache
def code_key() -> str:
    """The code the transcript is derived with, the same on every system (line ends aside)."""
    digest = hashlib.sha256()
    for path in sorted(p for name in DERIVED_FROM for p in sources(ROOT / name)):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def derive_key() -> str:
    """The code and the listening settings that change what is derived from a hearing."""
    from tarjim.listen.chunks import chunk_seconds
    from tarjim.listen.coverage import gap_seconds

    chosen = f"{code_key()}|chunk={chunk_seconds()}|gap={gap_seconds()}"
    return hashlib.sha256(chosen.encode()).hexdigest()[:16]


def keep_transcript(cache: Path, transcript: Transcript) -> None:
    data = {DERIVE: derive_key(), **asdict(transcript)}
    (cache / TRANSCRIPT).write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                    encoding="utf-8")


def kept_transcript(cache: Path) -> tuple[Transcript, bool] | None:
    """The kept transcript, and whether it was derived by the code and settings running now."""
    try:
        data = json.loads((cache / TRANSCRIPT).read_text(encoding="utf-8"))
        current = data.pop(DERIVE, None) == derive_key()
        words = [Word(**w) for w in data.pop("words")]
        return Transcript(words=words, **data), current
    except (OSError, ValueError, KeyError, TypeError):
        return None


def forget(cache: Path) -> None:
    """What a "listen again" clears: the hearing, what was asked again, its transcript and the
    lines made from them."""
    gone = [p for p in [cache / HEARD, cache / ASKED, cache / TRANSCRIPT,
                        *cache.glob(MADE_FROM_IT)] if p.exists()]
    for path in gone:
        path.unlink(missing_ok=True)
    print(f"listen again: cleared {len(gone)} kept file(s) for {cache.name}", flush=True)
