from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
from tarjim.findings import findings
from tarjim.gemini_client import QuotaExhausted
from tarjim.job import Job, checkpoint
from tarjim.listen.asked import TRIES
from tarjim.listen.kept import forget, keep_heard, keep_transcript, load_heard, reusable
from tarjim.listen.merge import Heard
from tarjim.models import Word

Regions = list[tuple[float, float]]


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
        return local_transcript(audio, error), False
    if heard.utterances:
        return listen_and_align(job, audio, heard, report)
    if heard.local_words is not None:  # the local listener itself heard no speech
        return Transcript(language=heard.language, text=""), False
    return local_transcript(audio), False


def heard_for(job: Job, audio: Path) -> Heard:
    """What was heard before, or a new hearing; kept once the lines are checked. A cloud hearing
    with no speech in it is kept too and heard again at most TRIES times across runs, or until
    the person asks to listen again (2026-11-08: it was paid for in full on every run)."""
    kept = load_heard(job.cache)
    if kept is not None and (kept.utterances or kept.empty >= TRIES):
        return kept
    heard = listen_video(job.video, audio)
    if not heard.utterances and heard.local_words is None and not heard.backup:
        keep_heard(job.cache, replace(heard, empty=(kept.empty if kept else 0) + 1))
    return heard


def listen_video(video: Path, audio: Path) -> Heard:
    """The chosen engine's hearing, or a backup's, marked so it is used but never kept."""
    from tarjim.engines.choice import chain

    failures: list[Exception] = []
    for rank, provider in enumerate(chain("listen")):
        checkpoint()  # a backup engine is never started for a job that was cancelled
        try:
            heard = listen_with(provider, video, audio)
            return replace(heard, provider=provider, backup=rank > 0)
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


def listen_and_align(job: Job, audio: Path, heard: Heard,
                     report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it covers all the speech, so it is worth keeping."""
    import soundfile

    from tarjim.listen.check import regions_in
    from tarjim.listen.settle import Sound, settled
    from tarjim.listen.whose import by_voice

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    # first: its times correct a cloud listener's drift; the local listener is its own
    local = heard.local_words
    opinion = second_opinion(audio, heard.language) if local is None else local
    done = settled(job, heard, Sound(wav, rate, regions_in(wav)), opinion)
    # shown on the job, the stretches given up too (2026-11-08)
    findings().heard(tuple((g.start, g.end) for g in done.left if not g.given_up),
                     done.agreement, tuple((g.start, g.end) for g in done.left if g.given_up))
    words = by_voice(done.transcript.words, wav, rate)
    return replace(done.transcript, words=words), done.whole and not heard.backup


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
