"""Each stretch of speech the transcript left out is heard again by the same engine, alone; when
that brings nothing, the words this computer heard there fill it. What cannot be filled is said
in the log, and the hearing is not kept, so the next run listens again (hearing.py)."""
from collections.abc import Callable
from dataclasses import dataclass

from tarjim.job import checkpoint
from tarjim.listen.coverage import Gap, Hearing, gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

PAD = 0.75  # seconds of sound either side of a stretch, so its first and last words are whole
OVERLAP = 0.5  # share of a heard-again line inside a line already there: the same speech
REPEATED = 0.6  # share of its words already said by a line close by: the same speech
NEAR = 3.0
LINE_PAUSE = 0.7  # local words become lines at pauses this long
LINE_WORDS = 12

Relisten = Callable[[float, float], list[Utterance]]


@dataclass(frozen=True)
class Mended:
    utterances: list[Utterance]
    added: list[Utterance]
    left: list[Gap]

    @property
    def whole(self) -> bool:
        return not self.left


def tokens(text: str) -> set[str]:
    return {norm(w) for w in split_words(text) if norm(w)}


def overlaps(line: Utterance, lines: list[Utterance]) -> bool:
    length = max(line.end - line.start, 0.01)
    return any(min(line.end, o.end) - max(line.start, o.start) > OVERLAP * length for o in lines)


def repeats(line: Utterance, lines: list[Utterance]) -> bool:
    mine = tokens(line.text)
    near = {t for o in lines if o.start - NEAR <= line.end and line.start <= o.end + NEAR
            for t in tokens(o.text)}
    return bool(mine) and len(mine & near) >= REPEATED * len(mine)


def from_words(words: list[Word]) -> list[Utterance]:
    groups: list[list[Word]] = []
    for word in words:
        if groups and word.start - groups[-1][-1].end < LINE_PAUSE and \
                len(groups[-1]) < LINE_WORDS:
            groups[-1].append(word)
        else:
            groups.append([word])
    return [Utterance(g[0].start, g[-1].end, g[0].speaker, " ".join(w.text for w in g))
            for g in groups]


def described(gap: Gap) -> str:
    said = f"{len(gap.words)} local words" if gap.words else "no words"
    return f"gap {gap.start:.1f}-{gap.end:.1f} s ({gap.speech:.1f} s of speech, {said})"


class Mender:
    def __init__(self, hearing: Hearing, relisten: Relisten | None, name: str) -> None:
        self.hearing, self.relisten, self.name = hearing, relisten, name or "the same engine"

    def heard_again(self, gap: Gap) -> list[Utterance]:
        if self.relisten is None:
            return []
        checkpoint()  # a cancel stops before another request
        try:
            return self.relisten(max(0.0, gap.start - PAD), gap.end + PAD)
        except (RuntimeError, OSError) as error:
            print(f"coverage: listening again with {self.name} failed: {str(error)[:200]}",
                  flush=True)
            return []

    def fill(self, gap: Gap, lines: list[Utterance]) -> tuple[list[Utterance], str]:
        found = self.heard_again(gap)
        again = [u for u in found if not overlaps(u, lines) and not repeats(u, lines)]
        if again:
            return again, f"re-listened with {self.name}: {len(again)} lines"
        if gap.words:
            return from_words(gap.words), f"filled from local words: {len(gap.words)} words"
        if self.hearing.local:  # the listener on this computer ran and heard no words here
            return [], "no listener heard words here; left as it is"
        return [], "not repaired"

    def mend(self) -> Mended:
        lines, added, left = list(self.hearing.utterances), [], []
        for gap in gaps(self.hearing):
            fresh, outcome = self.fill(gap, lines)
            print(f"coverage: {described(gap)} -> {outcome}", flush=True)
            lines.extend(fresh)
            added.extend(fresh)
            left.extend([gap] if outcome == "not repaired" else [])
        return Mended(sorted(lines, key=lambda u: u.start), added, left)


def mend(hearing: Hearing, relisten: Relisten | None, name: str) -> Mended:
    return Mender(hearing, relisten, name).mend()
