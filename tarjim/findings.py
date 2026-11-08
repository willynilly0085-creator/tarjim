"""What a job knows is not right once it is done, kept so the person sees it.

Before 2026-11-08 the app showed plain success when speech was left with no words, when a line
came back from no translation engine, or when the words were found far from where they were
timed: only the command line printed the checks, and the log the rest. Each step now writes what
it found here, and the server keeps it on the job (server/engine.py) for the page to show.
"""
import json
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tarjim.models import Cue
from tarjim.qa import Issue

Span = tuple[float, float]
Note = dict[str, Any]

# Below this share of words found where they are timed the subtitles may not follow the voice
# (listen/settle.py measured 0.56 and more on heated debates whose timing was right).
IN_SYNC = 0.5
READABILITY = ("reading_speed", "line_length", "too_many_lines")
SHOWN_TIMES = 5  # where the first few are; the count says how many there are
TIMING = "timing.json"  # the timing check of the transcript kept beside it


@dataclass
class Findings:
    left: list[Span] = field(default_factory=list)  # speech that still has no words
    agreement: float | None = None  # share of words found where they are timed; None: unchecked
    in_source: list[int] = field(default_factory=list)  # lines no engine translated: shown as said
    sounds: list[int] = field(default_factory=list)  # lines left empty as only a sound (Mm, Uh)
    over_budget: list[int] = field(default_factory=list)  # longer than their time allows
    stopped: Exception | None = None  # why an engine stopped, when lines were left as said

    def heard(self, left: tuple[Span, ...], agreement: float | None) -> None:
        self.left, self.agreement = list(left), agreement

    def notes(self, cues: list[Cue], issues: list[Issue]) -> list[Note]:
        """What the page lists under the finished job; a problem says the job is done with
        notes, a readability warning alone does not."""
        def at(numbers: list[int]) -> list[float]:
            return [cues[n - 1].start for n in sorted(set(numbers)) if 0 < n <= len(cues)]

        def kind(name: str) -> list[int]:
            return [issue.number for issue in issues if issue.kind == name]

        sounds = set(self.sounds)  # left empty on purpose; the check counts them untranslated
        readable = [*self.over_budget, *(i.number for i in issues if i.kind in READABILITY)]
        rows = [note("speech_left", [start for start, _end in self.left]),
                note("in_source", at(self.in_source)), *self.stop(),
                note("untranslated", at([n for n in kind("untranslated") if n not in sounds])),
                note("overlap", at(kind("overlap"))),
                note("readability", at(readable), problem=False),
                note("sounds", at(self.sounds), problem=False), *self.timing()]
        return [row for row in rows if row["count"]]

    def stop(self) -> list[Note]:
        """Why lines are shown as said: a used-up quota or a timed-out subscription said in the
        person's words (2026-11-08), where before the job looked done with no reason given."""
        if self.stopped is None or not self.in_source:
            return []
        from tarjim.server.evidence import evidence
        from tarjim.server.reasons import classify

        return [{"kind": "engine_stopped", "problem": True, "count": 1, "at": [],
                 "reason": classify(self.stopped), "detail": evidence(str(self.stopped))}]

    def remember(self, cache: Path) -> None:
        """Kept with the transcript, so a re-run from it still shows the timing check."""
        (cache / TIMING).write_text(json.dumps({"agreement": self.agreement}), encoding="utf-8")

    def recall(self, cache: Path) -> None:
        """The check of a kept transcript; one kept before 2026-11-08 has none: unchecked."""
        kept = cache / TIMING
        if kept.exists():
            self.agreement = json.loads(kept.read_text(encoding="utf-8")).get("agreement")

    def timing(self) -> list[Note]:
        if self.agreement is None or self.agreement >= IN_SYNC:
            return []
        return [{"kind": "timing", "problem": True, "count": 1, "at": [],
                 "share": round(self.agreement * 100)}]


def note(kind: str, at: list[float], problem: bool = True) -> Note:
    return {"kind": kind, "problem": problem, "count": len(at),
            "at": [round(time, 1) for time in at[:SHOWN_TIMES]]}


FINDINGS: ContextVar[Findings | None] = ContextVar("findings", default=None)


def collecting() -> Findings:
    """A fresh record for the job this thread runs."""
    found = Findings()
    FINDINGS.set(found)
    return found


def findings() -> Findings:
    """The running job's record, or a throwaway when nobody keeps one (the command line)."""
    return FINDINGS.get() or Findings()
