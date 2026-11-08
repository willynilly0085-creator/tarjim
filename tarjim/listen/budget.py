"""What one job may pay to ask about stretches again (2026-11-08). Every stretch left out was asked
with no limit: on a clip the voice detector cut into many pieces, or one whose kept transcript was
derived again after the code changed, each gap paid a request of three passes. The budget counts
requests and seconds of sound, not passes: twenty asks of 5 s are nothing beside the clip's own
listening, so a pass count alone left long clips unrepaired.

A stretch the budget refuses is not given up: it stays open, the transcript is not kept, and the
next run asks it (listen/repair.py), so only what is left over waits a run."""
from dataclasses import dataclass, field
from math import ceil

from tarjim.listen.merge import PASSES

REQUESTS = 9  # requests a job may always make
BASE = 3  # requests a job makes besides one a minute of the clip
AUDIO = 60.0  # seconds of sound a job may always send, each pass counted
SHARE = 0.1  # of the clip's length, when that is more
SUBSCRIPTION = "antigravity"  # the Gemini subscription: half the requests
SINGLE = "openai"  # heard in one pass a request

Span = tuple[float, float]


class Refused(RuntimeError):
    """The stretch is not asked about in this job: the budget is used, the quota is used up, or
    the same sound failed already. Not a `Spent`: the stretch stays open for the next run."""


@dataclass
class Budget:
    requests: int | None = None  # None: no limit (no engine pays for it)
    audio: float | None = None  # seconds of sound times passes
    passes: int = 1
    made: int = 0
    sent: float = 0.0
    refused: list[Span] = field(default_factory=list)
    rederive: bool = False  # asked because the kept transcript is derived again

    def over(self, cost: float) -> bool:
        """The first request of a job is heard whole however long it is, so a clip whose end
        was left out (2026-10-31: 62 s) is still asked about once."""
        if self.requests is None or self.audio is None:
            return False
        return self.made >= self.requests or (self.made > 0 and self.sent + cost > self.audio)

    def charge(self, span: Span) -> None:
        cost = (span[1] - span[0]) * self.passes
        if self.over(cost):
            self.refused.append(span)
            raise Refused(f"{span[0]:.1f}-{span[1]:.1f} s: the job's budget for asking again "
                          f"is used ({self.made} requests, {self.sent:.0f} s of sound)")
        self.made += 1
        self.sent += cost
        print(f"coverage: paid ask {self.made} of {self.requests} ({self.sent:.0f} of "
              f"{self.audio or 0:.0f} s of sound){self.why()}", flush=True)

    def why(self) -> str:
        return ", because the kept transcript is derived again" if self.rederive else ""

    def said(self) -> str:
        return (f"coverage: asked again {self.made} time(s) of {self.requests}, {self.sent:.0f} "
                f"of {self.audio or 0:.0f} s of sound; {len(self.refused)} stretch(es) refused "
                f"by the budget{self.why()}")


def budget_for(provider: str, seconds: float, rederive: bool = False) -> Budget:
    """At least REQUESTS requests and AUDIO seconds of sound; one more request a minute of the
    clip and a tenth of its length on longer clips; half the requests on a subscription."""
    passes = 1 if provider == SINGLE else PASSES
    requests = max(REQUESTS, BASE + ceil(seconds / 60))
    if provider == SUBSCRIPTION:
        requests = ceil(requests / 2)
    return Budget(requests, max(AUDIO, SHARE * seconds) * passes, passes, rederive=rederive)
