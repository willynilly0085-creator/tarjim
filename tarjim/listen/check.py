"""The step after hearing: speech no line covers is found and filled (listen/coverage.py,
listen/repair.py), then speech no timed word reaches (listen/wordcover.py), and the hearing is
kept only when nothing is left out."""
from dataclasses import replace
from pathlib import Path
from typing import Any

from tarjim import media
from tarjim.job import Job
from tarjim.listen.coverage import Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard
from tarjim.listen.merge import Heard
from tarjim.listen.novel import Again
from tarjim.listen.repair import Relisten, mend
from tarjim.listen.timing import Timer
from tarjim.listen.wordcover import Checked, recheck

Regions = list[tuple[float, float]]


def covered(job: Job, heard: Heard, hearing: Hearing, timer: Timer) -> Checked:
    """Speech no line covers is heard again, the lines are timed, then speech no timed word
    reaches is mended (listen/wordcover.py); the hearing is kept only when nothing is left out."""
    relisten = relistener(heard.provider, job.video)
    mended = mend(hearing, relisten, heard.provider)
    words = timer.whole(mended.utterances)
    checked = recheck(replace(hearing, utterances=mended.utterances), words, timer,
                      Again(relisten, heard.provider, mended.left))
    left = [*mended.left, *checked.left]
    if left:
        print(f"coverage: {len(left)} stretch(es) of speech still have no words; this "
              "hearing is not kept, the next run listens again", flush=True)
    else:
        keep_heard(job.cache, replace(heard, added=[*heard.added, *mended.added, *checked.added]))
    return replace(checked, left=left)


def relistener(provider: str, video: Path) -> Relisten | None:
    """The engine that heard the clip, asked about one stretch of it; the local listener's
    words are already at hand, so it is not asked again."""
    if provider in ("", "local"):
        return None
    from tarjim.hearing import cloud_listener
    from tarjim.listen.chunks import shift

    once = cloud_listener(provider)

    def again(start: float, end: float) -> list[Utterance]:
        return shift(once(media.audio_bytes(video, start, end)).utterances, (start, end))

    return again


def regions_in(wav: Any) -> Regions:
    try:
        from tarjim.asr.vad import speech_regions

        return speech_regions(wav)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f"speech: no voice detector ({type(error).__name__}); pieces are cut on time and "
              "coverage is checked against the local words alone", flush=True)
        return []
