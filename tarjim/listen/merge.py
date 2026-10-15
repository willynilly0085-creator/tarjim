from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass

from tarjim.gemini_client import QuotaExhausted
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import AGREE, vote

PASSES = 3
CLOSE = 0.9

Listen = Callable[[], tuple[str, list[Utterance]]]


@dataclass(frozen=True)
class Heard:
    language: str
    utterances: list[Utterance]
    passes: list[list[Utterance]]


def listen_many(listen: Listen, passes: int = PASSES) -> Heard:
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
    return Heard(results[0][0], settled(vote(runs, min(AGREE, len(runs))), runs), runs)


def spoken(run: list[Utterance]) -> int:
    return sum(len(u.text.split()) for u in run)


def settled(voted: list[Utterance], runs: list[list[Utterance]]) -> list[Utterance]:
    """Passes that hear the same words but place them seconds apart lose whole lines in the vote
    (measured with a Gemini subscription: three passes of 147 to 154 words voted down to 96).
    When the passes agree on how much was said and the vote kept clearly less, the fullest pass
    stands; the words are timed afterwards on this computer either way."""
    counts = sorted(spoken(run) for run in runs)
    agreed = len(runs) > 1 and counts[0] >= CLOSE * counts[-1]
    return max(runs, key=spoken) if agreed and spoken(voted) < CLOSE * counts[-1] else voted
