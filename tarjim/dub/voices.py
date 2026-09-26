from tarjim.models import Word

WANTED = 10.0
LONGEST = 12.0
SHORTEST = 1.2
MAX_GAP = 0.6

Span = tuple[float, float]


def stretches(words: list[Word]) -> list[tuple[str, Span]]:
    found: list[tuple[str, list[float]]] = []
    for word in words:
        last = found[-1] if found else None
        if last and last[0] == word.speaker and word.start - last[1][1] <= MAX_GAP:
            last[1][1] = word.end
        else:
            found.append((word.speaker, [word.start, word.end]))
    return [(speaker, (span[0], span[1])) for speaker, span in found]


def runs_by_speaker(words: list[Word]) -> dict[str, list[Span]]:
    runs: dict[str, list[Span]] = {}
    for speaker, span in stretches(words):
        if span[1] - span[0] >= SHORTEST:
            runs.setdefault(speaker, []).append(span)
    return runs


def pick(spans: list[Span]) -> list[Span]:
    chosen, total = [], 0.0
    for start, end in sorted(spans, key=lambda s: s[1] - s[0], reverse=True):
        if total >= WANTED:
            break
        take = min(end - start, LONGEST - total)
        chosen.append((start, start + take))
        total += take
    return sorted(chosen)


def reference_spans(words: list[Word]) -> dict[str, list[Span]]:
    return {speaker: pick(spans) for speaker, spans in runs_by_speaker(words).items()}
