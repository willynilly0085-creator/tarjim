"""The step after hearing: speech no line covers is found and filled (listen/coverage.py,
listen/repair.py), and the hearing is kept only when nothing is left out."""
from dataclasses import replace
from pathlib import Path
from typing import Any

from tarjim import media
from tarjim.job import Job
from tarjim.listen.coverage import Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard
from tarjim.listen.merge import Heard
from tarjim.listen.repair import Mended, Relisten, mend

Regions = list[tuple[float, float]]


def covered(job: Job, heard: Heard, hearing: Hearing) -> Mended:
    """Speech no line covers is heard again; the hearing is kept only when nothing is left out."""
    mended = mend(hearing, relistener(heard.provider, job.video), heard.provider)
    if mended.whole:
        keep_heard(job.cache, replace(heard, added=[*heard.added, *mended.added]))
    else:
        print(f"coverage: {len(mended.left)} stretch(es) of speech still have no words; this "
              "hearing is not kept, the next run listens again", flush=True)
    return mended


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
