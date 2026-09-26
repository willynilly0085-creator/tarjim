from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import AGREE, vote

PASSES = 3

Listen = Callable[[], tuple[str, list[Utterance]]]


@dataclass(frozen=True)
class Heard:
    language: str
    utterances: list[Utterance]
    passes: list[list[Utterance]]


def listen_many(listen: Listen, passes: int = PASSES) -> Heard:
    with ThreadPoolExecutor(max_workers=passes) as pool:
        futures = [pool.submit(listen) for _ in range(passes)]
        results = [f.result() for f in futures if f.exception() is None]
    if not results:
        raise RuntimeError("every listening pass failed")
    results.sort(key=lambda r: len(r[1]), reverse=True)
    runs = [utterances for _, utterances in results]
    return Heard(results[0][0], vote(runs, min(AGREE, len(runs))), runs)
