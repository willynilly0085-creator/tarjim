from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass, field

from tarjim import guards
from tarjim.gemini_client import QuotaExhausted
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import ordered, vote
from tarjim.models import Word
from tarjim.scripts import split_words

PASSES = 3
ONE_PASS = ("openai", "local")  # the listeners heard in one pass, whatever the setting
CLOSE = 0.9

Listen = Callable[[], tuple[str, list[Utterance]]]
Span = tuple[float, float]


@dataclass(frozen=True)
class Piece:
    """A piece of the clip heard on its own, with its passes at the piece's own times: a kept
    hearing is voted again piece by piece, the way it was heard (2026-11-08: the passes were
    voted again joined, so one broken line in one piece cost a reply in another)."""
    start: float
    end: float
    passes: list[list[Utterance]]
    language: str = ""  # as its listener named it; the clip's is the first piece's (2026-11-08)
    # 2026-11-09: the seconds of the piece before it that its request heard too, and each pass's
    # lines there at the request's own times: they only tell who is who (listen/links.py)
    lead_s: float = 0.0
    lead: list[list[Utterance]] = field(default_factory=list)

    @property
    def span(self) -> Span:
        return self.start, self.end


@dataclass(frozen=True)
class Fill:
    """A line that filled speech the hearing left out, and the stretch it filled; no stretch for
    the words' check's fills and those kept before 2026-11-08, which are judged by their words."""
    line: Utterance
    gap: Span | None = None


@dataclass(frozen=True)
class Heard:
    language: str
    utterances: list[Utterance]
    passes: list[list[Utterance]]
    # the words the local listener heard, when it was the listener: its own second opinion
    local_words: list[Word] | None = None
    provider: str = ""  # the engine that heard it: a stretch it left out is asked of it again
    added: list[Fill] = field(default_factory=list)  # what filled those stretches
    pieces: list[Piece] = field(default_factory=list)  # how a cloud listener heard it
    backup: bool = False  # heard by an engine after the chosen one: used, never kept
    empty: int = 0  # times the clip was heard with no speech in it, across runs
    asked: int = PASSES  # passes asked of each piece: a kept one asked for others is not reused


def listen_many(listen: Listen, passes: int | None = None) -> Heard:
    """The passes asked at once and voted on; as many as the job's listen.passes (2026-11-09),
    odd, so a word is kept by a real majority of them."""
    if passes is None:
        from tarjim.prefs.active import active

        passes = active().listen.passes
    with ThreadPoolExecutor(max_workers=passes) as pool:
        # each pass runs as part of the job: its programs are the job's, its cancel applies
        futures = [pool.submit(copy_context().run, listen) for _ in range(passes)]
        results = [f.result() for f in futures if f.exception() is None]
        errors = [e for f in futures if (e := f.exception()) is not None]
    if not results:
        if errors and all(isinstance(e, QuotaExhausted) for e in errors):
            raise errors[0]
        raise RuntimeError("every listening pass failed")
    results.sort(key=lambda r: len(r[1]), reverse=True)
    runs = [utterances for _, utterances in results]
    return Heard(results[0][0], agreed(runs), runs)


def sane(run: list[Utterance]) -> list[Utterance]:
    """The lines of a pass a person could have spoken. Only the broken line is left out: until
    2026-11-08 one such line cost the vote every other line of its pass, and with it the ending
    only that pass and one other had heard. A pass whose broken lines held more than a tenth of
    its words is still left out whole: the line or two it has left would otherwise vote down
    every line of the good pass they do not cover (2026-11-08)."""
    from tarjim.asr.sanity import plausible_line

    lines = [u for u in run if plausible_line(u.start, u.end, u.text)]
    if spoken(lines) >= CLOSE * spoken(run):
        guards.fired("merge.sane_line", len(run) - len(lines))
        return lines
    guards.fired("merge.sane_pass")
    return []


def agreed(runs: list[list[Utterance]]) -> list[Utterance]:
    """The vote over the lines a person could have spoken: a pass that put the whole speech in
    one 129-second line once became the vote's base and broke every time (asr/sanity.py). The
    agreement needed follows the passes that heard anything (vote.majority). A pass left with
    nothing is left out of the vote and of `settled` (2026-11-08: it counted as a pass that
    heard nothing, so the fullest pass no longer stood and the hearing could come out empty)."""
    cleaned = [run for whole in runs if (run := sane(whole))]
    kept = ordered(cleaned or runs)
    return settled(vote(kept), kept)


def spoken(run: list[Utterance]) -> int:
    return sum(len(split_words(u.text)) for u in run)


def settled(voted: list[Utterance], runs: list[list[Utterance]]) -> list[Utterance]:
    """Passes that hear the same words but place them seconds apart lose whole lines in the vote
    (measured with a Gemini subscription: three passes of 147 to 154 words voted down to 96).
    When the passes agree on how much was said and the vote kept clearly less, the fullest pass
    stands; the words are timed afterwards on this computer either way."""
    counts = sorted(spoken(run) for run in runs)
    agreed = len(runs) > 1 and counts[0] >= CLOSE * counts[-1]
    fullest = guards.when("merge.fullest", agreed and spoken(voted) < CLOSE * counts[-1])
    return max(runs, key=spoken) if fullest else voted
