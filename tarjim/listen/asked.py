"""The record of the stretches of a clip asked about again, kept beside its hearing
(listen/kept.py), so a stretch is paid for once a job and answered at most TRIES times across
runs."""
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from tarjim.gemini_client import QuotaExhausted
from tarjim.listen.budget import Budget, Refused
from tarjim.listen.gemini_listen import Utterance

ASKED = "asked.json"
TRIES = 2  # times a stretch is answered when asked about again, across runs
SAME = 0.5  # share of the shorter of two stretches they share: the same stretch
PAD = 0.75  # seconds of sound either side of a stretch, so its first and last words are whole

Span = tuple[float, float]
Relisten = Callable[[float, float], list[Utterance]]  # what is said in a stretch, in clip times


class Spent(Exception):
    """The stretch was asked about TRIES times already: it is not asked again."""


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
    a request that failed is no try, or two busy hours gave the speech up for good (2026-11-08).
    Since 2026-11-08 a job asks within its budget (listen/budget.py) and asks nothing more once
    the quota is used up; a refused stretch is no try either."""
    path: Path
    tries: list[list[float]]  # [start, end, times answered]
    answers: list[tuple[Span, list[Utterance]]] = field(default_factory=list)
    counted: list[Span] = field(default_factory=list)  # counted in this job
    budget: Budget = field(default_factory=Budget)
    exhausted: bool = False  # the engine's quota is used up: nothing more is asked in this job
    failed: list[Span] = field(default_factory=list)  # requests that failed in this job

    @classmethod
    def load(cls, cache: Path, budget: Budget | None = None) -> "Asked":
        try:
            data = json.loads((cache / ASKED).read_text(encoding="utf-8"))
            tries = [[float(a), float(b), int(n)] for a, b, n in data["asked"]]
        except (OSError, ValueError, KeyError, TypeError):
            tries = []
        return cls(cache / ASKED, tries, budget=budget or Budget())

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

    def stopped(self, start: float, end: float) -> None:
        """No request after a used-up quota, nor for sound that failed already in this job: until
        2026-11-08 the failure was taken for an answer that heard nothing, and with the local
        listener on, the stretch was dropped from the job."""
        if self.exhausted:
            raise Refused("the engine's quota is used up; nothing more is asked in this job")
        if any(first <= start and end <= last for first, last in self.failed):
            raise Refused(f"{start:.1f}-{end:.1f} s failed already in this job")

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
            self.stopped(start, end)
            self.budget.charge(span)
            return self.answered(relisten, span)

        return once

    def answered(self, relisten: Relisten, span: Span) -> list[Utterance]:
        try:
            lines = relisten(*span)
        except Exception as error:  # not asked again in this job, and no try
            self.exhausted = self.exhausted or isinstance(error, QuotaExhausted)
            self.failed.append(span)
            raise
        self.count(span)
        self.answers.append((span, lines))
        return lines
