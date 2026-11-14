"""The heard lines timed, then checked against the sound before anything is shown.

The words this computer heard (the second opinion) correct the cloud listener's times and fill
what it missed; when they are wrong, they move good lines to the wrong place. So once the lines
are timed, the aligner listens again (asr/agree.py): when too few words are found where they are
timed and a second opinion was used, the lines are timed again on the sound alone, and the timing
whose words are found more often is the one kept. The share found is written to the log, so a
clip whose subtitles drift from the voice can be told from one that does not.

Since 2026-11-08 the speech left out is filled once, before either timing, and both timings work
on the same repaired lines: before, each timing filled it again, asking Gemini again about the
same stretches, and kept the hearing it made, so the kept hearing could be the losing one's.

Since 2026-11-08 the hearing is kept as soon as the lines are mended, before either timing, and
again with the fills of the timing chosen. The transcript is worth keeping whenever no speech is
left to ask about again, whatever share of its words is found where they are timed: that share is
kept beside it (findings.py) so the job still warns, where before such a clip was timed again in
full on every run with the same result.
"""
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from tarjim import guards
from tarjim.asr.base import Transcript
from tarjim.asr.sanity import implausible
from tarjim.job import Job
from tarjim.listen.chunks import CLAMPED, placeable
from tarjim.listen.coverage import Gap, Hearing, open_gaps
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Fill, Heard
from tarjim.listen.placed import Placed, by_time, placed
from tarjim.models import Word

# The share of words found where they are timed that needs no second try. Measured on the
# owner's clips: 0.97 to 1.00 where the subtitles follow the voice, 0.56 to 0.79 in heated
# debates where two people talk at once (each one's letters are hard to find under the other's),
# 0.00 on the Somali chant whose timing had gone wrong.
IN_SYNC = 0.5
# Of the aligned words, how many the local words must hold to stand in for them: since
# 2026-11-08 they are only the runs the sound confirmed, and a few kept runs standing in for a
# whole clip would leave most of its speech with no subtitle.
STANDS_IN = 0.8
# moved to listen/placed.py on 2026-11-08 and still offered here
__all__ = ["Placed", "by_time", "placed"]

if TYPE_CHECKING:
    from tarjim.asr.speechmap import SpeechMap
    from tarjim.listen.check import Repair


@dataclass(frozen=True)
class Sound:
    wav: Any
    rate: int
    speech: list[tuple[float, float]]
    # where the local words the sound left out were timed (listen/opinion.doubted, 2026-11-08)
    doubted: list[tuple[float, float]] = field(default_factory=list)
    # every local word, by its text, to judge the passes by (listen/opinion.backing, 2026-11-09)
    said: list[Word] | None = None
    # the local words that fill speech left out (listen/opinion.held, 2026-11-09)
    held: list[Word] = field(default_factory=list)
    # the clip's speech map every timing reads (listen/clipmap.py, 2026-11-09); `speech` is its
    # speech, the detector's with what the letters alone heard
    speech_map: "SpeechMap | None" = None


@dataclass(frozen=True)
class Timed:
    transcript: Transcript
    whole: bool  # no speech is left to ask about again, so it is worth keeping
    agreement: float | None
    added: list[Utterance] = field(default_factory=list)  # what the words' check filled
    # speech still without words, shown on the job, with the stretches given up
    left: list[Gap] = field(default_factory=list)
    passes: int = 0  # how often the clip's letters were heard so far in this run
    # every line that filled speech the hearing left out (listen/witness.py, 2026-11-14)
    fills: list[Fill] = field(default_factory=list)


def worth_keeping(left: list[Gap]) -> bool:
    """No speech left to ask about again. Changed 2026-11-08: a timing whose words were found
    seldom where they are placed was not kept either, and every later run timed it again."""
    return not open_gaps(left)


def trusted(words: list[Word], opinion: list[Word]) -> list[Word]:
    enough = len(opinion) >= STANDS_IN * len(words)
    if implausible(words) and enough and not implausible(opinion):
        guards.fired("settle.trusted")
        print(f"timing: {len(words)} words timed faster than speech; using the words this "
              "computer heard", flush=True)
        return opinion
    return words


def timed(repair: "Repair", hearing: Hearing, sound: Sound) -> Timed:
    """The repaired lines timed with the words in `hearing.local`, or on the sound alone."""
    from tarjim.listen.check import rechecked
    from tarjim.listen.timing import Timer

    timer = Timer(sound.wav, sound.rate, repair.language, hearing.local, sound.speech_map)
    checked = rechecked(repair, hearing, timer)
    words = trusted(checked.words, hearing.local)
    text = " ".join(u.text for u in checked.utterances)
    agreement = timer.agreement(words)
    return Timed(Transcript(language=repair.language, text=text, words=words),
                 worth_keeping(checked.left), agreement, checked.added, checked.left,
                 timer.passes())


def share(agreement: float | None) -> str:
    return "could not be checked" if agreement is None else f"{agreement:.0%} found"


def better(first: Timed, alone: Callable[[], Timed], second_opinion: bool) -> Timed:
    """The timing whose words are found where they are timed, with a second opinion or without."""
    print(f"timing check: {share(first.agreement)} where they are timed", flush=True)
    if not second_opinion or first.agreement is None or first.agreement >= IN_SYNC:
        return told(first, first)
    other = alone()
    guards.fired("settle.second_timing")
    print(f"timing check: on the sound alone, {share(other.agreement)}", flush=True)
    won = guards.when("settle.alone_won", (other.agreement or 0.0) > first.agreement)
    return told(other if won else first, other)


def told(kept: Timed, last: Timed) -> Timed:
    """How often the whole clip's letters were heard in this run, said once at its end: once is
    right, more means a slice or a check heard the sound again (2026-11-08)."""
    print(f"timing: the aligner heard the clip's letters {last.passes} time(s)", flush=True)
    return kept


def timeable(found: Placed) -> Placed:
    """The lines placed less those whose time is not known (chunks.placeable, 2026-11-08)."""
    moved = placeable(found.moved)
    return replace(found, own=[u for u in found.own if u.prior > CLAMPED], moved=moved)


def settled(job: Job, heard: Heard, sound: Sound, opinion: list[Word]) -> Timed:
    """Speech left out filled once and the hearing kept, the lines timed with the second opinion
    and, when that is off the voice, without it; the hearing kept with the fills of the timing
    chosen."""
    from tarjim.listen import budget
    from tarjim.listen.asked import Asked
    from tarjim.listen.check import keep, paid, repaired
    from tarjim.listen.kept import rederiving
    from tarjim.listen.soundtime import where_heard

    seconds = len(sound.wav) / sound.rate
    # each line where the sound holds it, before speech with no words is looked for (2026-11-14)
    found = where_heard(timeable(placed(heard, opinion, seconds, sound.said)), sound.wav,
                        heard.language)
    # one budget for every stretch asked again in this job (2026-11-08)
    asked = Asked.load(job.cache, budget.budget_for(heard.provider, seconds,
                                                    rederiving(job.cache)))
    # every check reads the clip's speech map, so a stretch is judged the same whether the local
    # listener ran or not (2026-11-09)
    heard_by = Hearing(found.moved, opinion, sound.speech, sound.doubted, sound.held,
                       sound.speech_map)
    repair = repaired(job, heard, heard_by, asked)
    fills = [*found.fills, *repair.mended.fills]
    keep(job, replace(heard, added=fills), asked, [])  # before any timing (2026-11-08)
    first = timed(repair, replace(heard_by, utterances=repair.mended.utterances), sound)
    lines = by_time([*found.own, *repair.mended.added])
    alone = Hearing(lines, [], sound.speech, map=sound.speech_map)
    chosen = better(first, lambda: timed(repair, alone, sound), bool(opinion))
    words = [Fill(line) for line in chosen.added]  # judged by their words on a later run
    keep(job, replace(heard, added=[*fills, *words]), asked, chosen.left)
    paid(asked, chosen.left)
    return replace(chosen, fills=[*fills, *words])
