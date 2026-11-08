"""Each stretch of speech the transcript left out is heard again by the same engine, alone; when
that brings nothing, the words this computer heard there fill it. What cannot be filled is said in
the log. Since 2026-11-08 the hearing is kept all the same and only that stretch is asked about
again on the next run, at most TRIES times in all (listen/asked.py); after that it is left as it
is, and the log says no listener heard it. Since 2026-11-08 such a stretch is still listed (given
up), so the job page shows it, where before it was dropped and the job looked whole."""
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from tarjim.job import checkpoint
from tarjim.listen.asked import TRIES, Spent
from tarjim.listen.coverage import Gap, Hearing, gaps, open_gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Fill
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

OVERLAP = 0.5  # share of a heard-again line inside a line already there: the same speech
REPEATED = 0.6  # share of its words already said by a line close by: the same speech
NEAR = 3.0
LINE_PAUSE = 0.7  # local words become lines at pauses this long
LINE_WORDS = 12
TURN_GAP = 0.3  # seconds: a line this close to a turn goes on with it
MAIN = "S1"  # the speaker of a line with no turn heard anywhere
NOT_REPAIRED = "not repaired"
NOT_ASKED = "not asked again"

Relisten = Callable[[float, float], list[Utterance]]  # asked about a gap, in clip times


@dataclass(frozen=True)
class Mended:
    utterances: list[Utterance]
    added: list[Utterance]
    left: list[Gap]  # with the stretches given up, which do not count against `whole`
    fills: list[Fill] = field(default_factory=list)  # what was added, with the stretch it filled

    @property
    def whole(self) -> bool:
        return not open_gaps(self.left)


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


def apart(line: Utterance, turn: Utterance) -> float:
    return max(turn.start - line.end, line.start - turn.end, 0.0)


def adjacent(line: Utterance, turns: list[Utterance]) -> list[Utterance]:
    before = [t for t in turns if t.end <= line.start]
    after = [t for t in turns if t.start >= line.end]
    return [*([max(before, key=lambda t: t.end)] if before else []),
            *([min(after, key=lambda t: t.start)] if after else [])]


def speaker_of(line: Utterance, turns: list[Utterance]) -> str:
    """The speaker of the turn next to the line, when it is closer than TURN_GAP, else of the
    nearest turn."""
    speaking = [t for t in turns if t.speaker]
    close = [t for t in adjacent(line, speaking) if apart(line, t) < TURN_GAP]
    found = min(close or speaking, key=lambda t: apart(line, t), default=None)
    return found.speaker if found else line.speaker or MAIN


def voiced(fills: list[Utterance], lines: list[Utterance]) -> list[Utterance]:
    """Lines made from the local words, which name no speaker, each with the speaker of the turn
    it goes on with: before 2026-11-08 they had none and were shown in the main colour."""
    out: list[Utterance] = []
    for line in fills:
        out.append(replace(line, speaker=line.speaker or speaker_of(line, [*lines, *out])))
    return out


def described(gap: Gap) -> str:
    said = f"{len(gap.words)} local words" if gap.words else "no words"
    return f"gap {gap.start:.1f}-{gap.end:.1f} s ({gap.speech:.1f} s of speech, {said})"


class Mender:
    label = ""  # what the log calls the check: "" for lines, "words " after alignment

    def __init__(self, hearing: Hearing, relisten: Relisten | None, name: str) -> None:
        self.hearing, self.relisten, self.name = hearing, relisten, name or "the same engine"

    def heard_again(self, gap: Gap) -> list[Utterance] | None:
        """What the engine hears in the stretch now, with a little sound either side (the job's
        record adds it, listen/kept.py); None when no engine is asked about it any more: there is
        none, or it answered TRIES times across runs. A failed request is [], so the stretch is
        left for the next run to ask again."""
        if self.relisten is None:
            return None
        checkpoint()  # a cancel stops before another request
        try:
            return self.relisten(gap.start, gap.end)
        except Spent:
            return None
        except (RuntimeError, OSError) as error:
            print(f"coverage: listening again with {self.name} failed: {str(error)[:200]}",
                  flush=True)
            return []

    def novel(self, line: Utterance, lines: list[Utterance]) -> bool:
        return not overlaps(line, lines) and not repeats(line, lines)

    def from_local(self, gap: Gap, lines: list[Utterance]) -> list[Utterance]:
        """The local words as lines, less those a line close by already says: a cloud line
        timed a little off leaves a gap its own words fill, and the sentence was shown twice
        ("I apologize, Jim, if things got heated", 2026-11-08)."""
        return voiced([u for u in from_words(gap.words) if not repeats(u, lines)], lines)

    def in_transcript(self, _gap: Gap) -> str | None:
        """Whether the local words left out here are said where the transcript is timed. Lines
        have no word times yet, so the check after alignment tells (listen/wordcover.py): until
        2026-11-08 a gap was called filled here, and kept, whenever a line close by said its
        words, wherever that line's words were timed."""
        return "the local words here are said by a line close by; checked once it is timed"

    def unfilled(self, gap: Gap, asking: bool) -> str:
        said = self.in_transcript(gap) if gap.words else None
        if said:
            return said
        if self.hearing.local and not gap.words:  # the listener on this computer ran here
            return "no listener heard words here; left as it is"
        if not asking:
            heard = ("the local words here repeat a line timed elsewhere" if gap.words
                     else "heard by no listener")
            return f"{heard}; {NOT_ASKED} ({TRIES} times at most), left as it is"
        return NOT_REPAIRED

    def fill(self, gap: Gap, lines: list[Utterance]) -> tuple[list[Utterance], str]:
        heard = self.heard_again(gap)
        again = [u for u in heard or [] if self.novel(u, lines)]
        if again:
            return again, f"re-listened with {self.name}: {len(again)} lines"
        local = self.from_local(gap, lines)
        if local:
            return local, f"filled from local words: {len(gap.words)} words"
        return [], self.unfilled(gap, heard is not None)

    def mend(self, found: list[Gap] | None = None) -> Mended:
        lines, left = list(self.hearing.utterances), []
        fills: list[Fill] = []
        for gap in gaps(self.hearing) if found is None else found:
            fresh, outcome = self.fill(gap, lines)
            print(f"coverage: {self.label}{described(gap)} -> {outcome}", flush=True)
            lines.extend(fresh)
            fills.extend(Fill(line, (gap.start, gap.end)) for line in fresh)
            left.extend(still_left(gap, outcome))
        return Mended(sorted(lines, key=lambda u: u.start), [f.line for f in fills], left, fills)


def still_left(gap: Gap, outcome: str) -> list[Gap]:
    """The stretch, when nothing filled it: to be asked again, or given up but still listed."""
    if outcome == NOT_REPAIRED:
        return [gap]
    return [replace(gap, given_up=True)] if NOT_ASKED in outcome else []


def mend(hearing: Hearing, relisten: Relisten | None, name: str) -> Mended:
    return Mender(hearing, relisten, name).mend()
