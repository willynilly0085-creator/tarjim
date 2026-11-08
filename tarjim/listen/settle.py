"""The heard lines timed, then checked against the sound before anything is shown.

The words this computer heard (the second opinion) correct the cloud listener's times and fill
what it missed; when they are wrong, they move good lines to the wrong place. So once the lines
are timed, the aligner listens again (asr/agree.py): when too few words are found where they are
timed and a second opinion was used, the lines are timed again on the sound alone, and the timing
whose words are found more often is the one kept. The share found is written to the log, so a
clip whose subtitles drift from the voice can be told from one that does not.
"""
from dataclasses import dataclass
from typing import Any

from tarjim.asr.base import Transcript
from tarjim.asr.sanity import implausible
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word

# The share of words found where they are timed that needs no second try. Measured on the
# owner's clips: 0.97 to 1.00 where the subtitles follow the voice, 0.56 to 0.79 in heated
# debates where two people talk at once (each one's letters are hard to find under the other's),
# 0.00 on the Somali chant whose timing had gone wrong.
IN_SYNC = 0.5


@dataclass(frozen=True)
class Sound:
    wav: Any
    rate: int
    speech: list[tuple[float, float]]


@dataclass(frozen=True)
class Timed:
    transcript: Transcript
    whole: bool  # it covers all the speech, so it is worth keeping
    agreement: float | None


def placed(heard: Heard, opinion: list[Word], duration: float) -> list[Utterance]:
    """The hearing the audio backs most, at the times the audio backs, with what filled the
    stretches it left out on an earlier run."""
    from tarjim.asr.anchor import anchor
    from tarjim.listen.recover import best_heard

    chosen = best_heard(heard.utterances, heard.passes, opinion)
    return sorted([*anchor(chosen, opinion, duration), *heard.added], key=lambda u: u.start)


def trusted(words: list[Word], opinion: list[Word]) -> list[Word]:
    if implausible(words) and opinion and not implausible(opinion):
        print(f"timing: {len(words)} words timed faster than speech; using the words this "
              "computer heard", flush=True)
        return opinion
    return words


def timed(job: Job, heard: Heard, sound: Sound, opinion: list[Word]) -> Timed:
    from tarjim.listen.check import covered
    from tarjim.listen.coverage import Hearing
    from tarjim.listen.timing import Timer

    utterances = placed(heard, opinion, len(sound.wav) / sound.rate)
    timer = Timer(sound.wav, sound.rate, heard.language, opinion)
    checked = covered(job, heard, Hearing(utterances, opinion, sound.speech), timer)
    words = trusted(checked.words, opinion)
    text = " ".join(u.text for u in checked.utterances)
    transcript = Transcript(language=heard.language, text=text, words=words)
    return Timed(transcript, not checked.left, timer.agreement(words))


def share(agreement: float | None) -> str:
    return "could not be checked" if agreement is None else f"{agreement:.0%} found"


def settled(job: Job, heard: Heard, sound: Sound, opinion: list[Word]) -> Timed:
    """The timing whose words are found where they are timed, with a second opinion or without."""
    first = timed(job, heard, sound, opinion)
    print(f"timing check: {share(first.agreement)} where they are timed", flush=True)
    if not opinion or first.agreement is None or first.agreement >= IN_SYNC:
        return first
    alone = timed(job, heard, sound, [])
    print(f"timing check: on the sound alone, {share(alone.agreement)}", flush=True)
    return alone if (alone.agreement or 0.0) > first.agreement else first
