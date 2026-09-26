from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from tarjim.listen.gemini_listen import Utterance

MARGIN = 0.2
PASSES = 2

Listen = Callable[[], tuple[str, list[Utterance]]]


def overlaps(a: Utterance, b: Utterance) -> bool:
    return a.start < b.end + MARGIN and b.start < a.end + MARGIN


def merge(primary: list[Utterance], extra: list[Utterance], tag: str) -> list[Utterance]:
    added = [
        Utterance(u.start, u.end, f"{tag}{u.speaker}", u.text)
        for u in extra if not any(overlaps(u, p) for p in primary)
    ]
    return sorted(primary + added, key=lambda u: u.start)


def listen_many(listen: Listen, passes: int = PASSES) -> tuple[str, list[Utterance]]:
    with ThreadPoolExecutor(max_workers=passes) as pool:
        futures = [pool.submit(listen) for _ in range(passes)]
        results = [f.result() for f in futures if f.exception() is None]
    if not results:
        raise RuntimeError("every listening pass failed")
    results.sort(key=lambda r: len(r[1]), reverse=True)
    language, merged = results[0]
    for index, (_, utterances) in enumerate(results[1:], start=2):
        merged = merge(merged, utterances, tag=f"p{index}.")
    return language, merged
