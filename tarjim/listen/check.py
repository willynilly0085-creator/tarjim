"""The step after hearing: speech no line covers is found and filled (listen/coverage.py,
listen/repair.py), once, before any timing; then, in each timing, speech no timed word reaches
(listen/wordcover.py). Every stretch asked about again goes through one record per job
(listen/kept.py), so the lines check, the words check and both timings in listen/settle.py never
pay twice for the same stretch. The hearing is kept once the timing is chosen, even when speech
is left without words: only those stretches are asked about again on the next run."""
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from tarjim import media
from tarjim.job import Job
from tarjim.listen.coverage import Gap, Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import TRIES, Asked, keep_heard
from tarjim.listen.merge import Heard
from tarjim.listen.novel import Again
from tarjim.listen.repair import Mended, Relisten, mend
from tarjim.listen.timing import Timer
from tarjim.listen.wordcover import Checked, recheck

Regions = list[tuple[float, float]]


@dataclass(frozen=True)
class Repair:
    """The lines' check, made once for every timing tried after it."""
    language: str
    again: Again  # how a stretch is asked about again, and what the lines' check left
    mended: Mended


def repaired(job: Job, heard: Heard, hearing: Hearing, asked: Asked) -> Repair:
    relisten = relistener(heard.provider, job.video, asked)
    mended = mend(hearing, relisten, heard.provider)
    return Repair(heard.language, Again(relisten, heard.provider, mended.left), mended)


def rechecked(repair: Repair, hearing: Hearing, timer: Timer) -> Checked:
    """The lines timed, then speech no timed word reaches is mended (listen/wordcover.py)."""
    words = timer.whole(hearing.utterances)
    checked = recheck(hearing, words, timer, repair.again)
    return replace(checked, left=[*repair.mended.left, *checked.left])


def keep(job: Job, heard: Heard, asked: Asked, left: list[Gap]) -> None:
    """The hearing of the timing chosen, with what was asked again. Until 2026-11-08 one stretch
    left without words meant the hearing was not kept and every run paid to listen again."""
    keep_heard(job.cache, heard)
    asked.save()
    if left:
        print(f"coverage: {len(left)} stretch(es) of speech still have no words; the hearing is "
              f"kept and only they are asked about again on the next run ({TRIES} times at "
              "most)", flush=True)


def relistener(provider: str, video: Path, asked: Asked) -> Relisten | None:
    """The engine that heard the clip, asked about one stretch of it (and a little sound either
    side) through the job's record; the local listener's words are already at hand, so it is not
    asked again."""
    if provider in ("", "local"):
        return None
    from tarjim.hearing import cloud_listener
    from tarjim.listen.chunks import shift

    once = cloud_listener(provider)

    def again(start: float, end: float) -> list[Utterance]:
        return shift(once(media.audio_bytes(video, start, end)).utterances, (start, end))

    return asked.asking(again)


def regions_in(wav: Any) -> Regions:
    try:
        from tarjim.asr.vad import speech_regions

        return speech_regions(wav)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"speech: no voice detector ({type(error).__name__}); pieces are cut on time and "
              "coverage is checked against the local words alone", flush=True)
        return []
