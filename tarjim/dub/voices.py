from dataclasses import replace

from tarjim.dub.lines import Line
from tarjim.models import Word
from tarjim.speakers import ranked, who

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


def one_voice_each(words: list[Word], lines: list[Line]) -> tuple[list[Word], list[Line]]:
    """Listener labels become voices: "voice1" for the speaker who talks most in each piece of
    the video, so one person is not handed a new voice in every piece or voting pass."""
    ranks = ranked(words)
    names = {w.speaker: f"voice{ranks[who(w.speaker)] + 1}" for w in words if w.speaker}
    return ([replace(w, speaker=names.get(w.speaker, w.speaker)) for w in words],
            [replace(line, speaker=names.get(line.speaker, line.speaker)) for line in lines])


def reference_spans(words: list[Word]) -> dict[str, list[Span]]:
    return {speaker: pick(spans) for speaker, spans in runs_by_speaker(words).items()}
