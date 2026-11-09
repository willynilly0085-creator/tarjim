from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
from tarjim.findings import findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.job import Job, checkpoint
from tarjim.listen.asked import TRIES
from tarjim.listen.heard_align import listen_and_align
from tarjim.listen.kept import forget, keep_heard, keep_transcript, load_heard, reusable
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.prefs.active import active

Regions = list[tuple[float, float]]
# Said when the chosen listener heard nothing and the person keeps this computer's listener
# from standing in (listen.local_backup, 2026-11-09): never a video quietly left with no lines.
NO_STAND_IN = ("listening: the chosen listener heard no speech, and the listener on this "
               "computer is turned off as its backup in the settings")
# moved to listen/heard_align.py on 2026-11-08 and still offered here; the names tests and the
# bench put other code in place of (cloud_listener, second_opinion, qwen_transcript) stay here
__all__ = ["listen_and_align"]


def transcript_for(job: Job, report: Callable[[str], None] = print) -> Transcript:
    if job.relisten:  # the person asked: nothing kept from an earlier hearing is used
        forget(job.cache)
    kept = reusable(job.cache)
    if kept is not None:
        findings().recall(job.cache)  # its timing check is shown again (2026-11-08)
        return kept
    from tarjim.memory import free_for_listening

    free_for_listening()
    audio = job.cache / "audio.wav"
    try:
        media.extract_audio(job.video, audio)
        transcript, lasting = hear(job, audio, report)
    finally:
        audio.unlink(missing_ok=True)
    if lasting:  # a backup's hearing, one that left speech to ask about again, or hearing
        # nothing, is tried afresh on the next run; one off the voice is kept with its share
        # found, so the job still warns (2026-11-08)
        keep_transcript(job.cache, transcript)
        findings().remember(job.cache)
    return transcript


def hear(job: Job, audio: Path, report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it is the chosen listener's own and worth keeping."""
    try:
        heard = heard_for(job, audio)
    except QuotaExhausted:
        raise
    except RuntimeError as error:
        return stand_in(audio, error), False
    if heard.utterances:
        return listen_and_align(job, audio, heard, report)
    if heard.local_words is not None:  # the local listener itself heard no speech
        return Transcript(language=heard.language, text=""), False
    return stand_in(audio), False


def stand_in(audio: Path, failure: RuntimeError | None = None) -> Transcript:
    """This computer's listener in place of the chosen one, unless the person turned it off."""
    if not active().listen.local_backup:
        raise failure or RuntimeError(NO_STAND_IN)
    return local_transcript(audio, failure)


def heard_for(job: Job, audio: Path) -> Heard:
    """What was heard before, or a new hearing; kept once the lines are checked. A cloud hearing
    with no speech in it is kept too and heard again at most TRIES times across runs, or until
    the person asks to listen again (2026-11-08: it was paid for in full on every run)."""
    kept = load_heard(job.cache)
    if kept is not None and kept.asked != asked_for(kept.provider):
        kept = None  # heard in another number of passes: heard again (2026-11-09)
    if kept is not None and (kept.utterances or kept.empty >= TRIES):
        return kept
    heard = listen_video(job.video, audio)
    if not heard.utterances and heard.local_words is None and not heard.backup:
        keep_heard(job.cache, replace(heard, empty=(kept.empty if kept else 0) + 1))
    return heard


def asked_for(provider: str) -> int:
    """How many passes a clip is heard in: the person's count, one for a single listener."""
    from tarjim.listen.merge import ONE_PASS

    return 1 if provider in ONE_PASS else active().listen.passes


def listen_video(video: Path, audio: Path) -> Heard:
    """The chosen engine's hearing, or a backup's, marked so it is used but never kept."""
    from tarjim.engines.choice import tried

    failures: list[Exception] = []
    for rank, provider in enumerate(tried("listen", active().listen.local_backup)):
        checkpoint()  # a backup engine is never started for a job that was cancelled
        try:
            heard = listen_with(provider, video, audio)
            return replace(heard, provider=provider, backup=rank > 0,
                           asked=asked_for(provider))
        except (RuntimeError, OSError) as error:
            failures.append(error)
    raise failures[-1] if failures else RuntimeError("no listening engine")


def listen_with(provider: str, video: Path, audio: Path) -> Heard:
    from tarjim.listen.chunks import is_long, listen_in_chunks

    if provider == "local":
        from tarjim.engines.local_listen import listen_file

        language, utterances, words = listen_file(audio)
        return Heard(language, utterances, [utterances], words)
    duration = media.wav_seconds(audio)  # the file's header may claim any length it likes
    once = cloud_listener(provider)

    def listen_span(start: float, end: float) -> Heard:
        return once(media.audio_bytes(video, start, end if end > start else None))

    regions = speech_regions_of(audio) if is_long(duration) else []
    return listen_in_chunks(duration, regions, listen_span)


def cloud_listener(provider: str) -> Callable[[bytes], Heard]:
    if provider == "openai":
        from tarjim.engines.openai_api import listen as openai_listen

        def single(sound: bytes) -> Heard:
            language, utterances = openai_listen(sound)
            return Heard(language, utterances, [utterances])

        return single
    from tarjim.listen.gemini_listen import listen
    from tarjim.listen.merge import listen_many

    if provider == "antigravity":  # the Gemini subscription hears through its own program
        from tarjim.engines.antigravity import AntigravityAsker

        return lambda sound: listen_many(lambda: listen(sound, AntigravityAsker()))
    return lambda sound: listen_many(lambda: listen(sound))


def speech_regions_of(audio: Path) -> Regions:
    """Where the pauses are, for cutting; with no voice detector the pieces are cut on time."""
    import soundfile

    from tarjim.listen.check import regions_in

    wav, _ = soundfile.read(str(audio), dtype="float32")
    return regions_in(wav)


def second_opinion(audio: Path, language: str = "") -> list[Word]:
    """The words this computer heard, when they are in the language the clip was heard in."""
    from tarjim.listen.opinion import agreeing

    try:
        heard = qwen_transcript(audio)
    except (RuntimeError, ValueError, MemoryError, OSError, ImportError) as error:
        # said once, with why: before 2026-11-08 a computer that could not run it lost the
        # second opinion with no trace in the log
        print(f"timing: no words from the listener on this computer ({type(error).__name__}: "
              f"{str(error)[:200]}); the lines are timed on the sound alone", flush=True)
        return []
    return agreeing(heard.words, heard.language, language)


def local_transcript(audio: Path, failure: RuntimeError | None = None) -> Transcript:
    """What is left when the chosen listener heard nothing or failed. When the local listener
    cannot run, the person sees the chosen listener's own error; a video in which it heard no
    speech (music alone) gets no subtitles. Since 2026-11-08 a computer too weak to run it (out
    of memory) is that case too, where before the job failed with the memory error."""
    try:
        return qwen_transcript(audio)
    except (RuntimeError, ValueError, MemoryError, OSError, ImportError) as error:
        print(f"listening: the listener on this computer could not stand in "
              f"({type(error).__name__}: {str(error)[:200]})", flush=True)
        if failure is not None:
            raise failure from error
        return Transcript(language="", text="")


def qwen_transcript(audio: Path) -> Transcript:
    from tarjim.asr.qwen import shared_engine
    from tarjim.memory import heavy

    with heavy():
        return shared_engine().transcribe(str(audio))
