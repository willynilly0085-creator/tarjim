import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
from tarjim.asr.sanity import implausible
from tarjim.gemini_client import QuotaExhausted
from tarjim.job import Job, checkpoint
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, agreed
from tarjim.models import Word

Regions = list[tuple[float, float]]


def transcript_for(job: Job, report: Callable[[str], None] = print) -> Transcript:
    cached = job.cache / "transcript.json"
    if cached.exists() and not implausible(Transcript.load(cached).words):
        return Transcript.load(cached)  # a broken timing kept by an older run is made again
    from tarjim.memory import free_for_listening

    free_for_listening()
    audio = job.cache / "audio.wav"
    try:
        media.extract_audio(job.video, audio)
        transcript, lasting = hear(job, audio, report)
    finally:
        audio.unlink(missing_ok=True)
    if lasting:  # a backup's hearing, or hearing nothing, is tried afresh on the next run
        transcript.save(cached)
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
        return listen_and_align(audio, heard, report), True
    if heard.local_words is not None:  # the local listener itself heard no speech
        return Transcript(language=heard.language, text=""), False
    return local_transcript(audio), False


def heard_for(job: Job, audio: Path) -> Heard:
    cached = job.cache / "heard.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        words = data.get("local_words")
        passes = [[Utterance(**u) for u in run] for run in data.get("passes") or []]
        voted = agreed(passes) if passes else [Utterance(**u) for u in data["utterances"]]
        return Heard(data["language"], voted, passes,
                     None if words is None else [Word(**w) for w in words])
    heard = listen_video(job.video, audio)
    if heard.utterances:  # hearing nothing is not kept: the next run listens again
        cached.write_text(json.dumps(asdict(heard), ensure_ascii=False, indent=1),
                          encoding="utf-8")
    return heard


def listen_video(video: Path, audio: Path) -> Heard:
    from tarjim.engines.choice import chain

    failures: list[Exception] = []
    for provider in chain("listen"):
        checkpoint()  # a backup engine is never started for a job that was cancelled
        try:
            return listen_with(provider, video, audio)
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
    import soundfile

    from tarjim.asr.vad import speech_regions

    wav, _ = soundfile.read(str(audio), dtype="float32")
    return speech_regions(wav)


def listen_and_align(audio: Path, heard: Heard, report: Callable[[str], None]) -> Transcript:
    import soundfile

    from tarjim.asr.align import shared_aligner
    from tarjim.asr.anchor import anchor
    from tarjim.asr.fuse import fuse
    from tarjim.listen.recover import best_heard
    from tarjim.memory import heavy

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    # first: its times correct a cloud listener's drift; the local listener is its own
    local = heard.local_words
    opinion = second_opinion(audio) if local is None else local
    chosen = best_heard(heard.utterances, heard.passes, opinion)  # what the audio backs most
    utterances = anchor(chosen, opinion, len(wav) / rate)
    with heavy():
        words = shared_aligner().align(wav, utterances, heard.language)
    words = fuse(words, utterances, opinion)
    if implausible(words) and opinion and not implausible(opinion):
        print(f"timing: {len(words)} words timed faster than speech; using the words this "
              "computer heard", flush=True)
        words = opinion
    return Transcript(language=heard.language, text=" ".join(u.text for u in utterances),
                      words=words)


def second_opinion(audio: Path) -> list[Word]:
    try:
        return qwen_transcript(audio).words
    except (RuntimeError, ValueError, MemoryError, OSError, ImportError):
        return []


def local_transcript(audio: Path, failure: RuntimeError | None = None) -> Transcript:
    """What is left when the chosen listener heard nothing or failed. Without the local
    listener, the person sees the chosen listener's own error; a video in which it heard no
    speech (music alone) gets no subtitles."""
    try:
        return qwen_transcript(audio)
    except (OSError, ImportError) as error:
        if failure is not None:
            raise failure from error
        return Transcript(language="", text="")


def qwen_transcript(audio: Path) -> Transcript:
    from tarjim.asr.qwen import shared_engine
    from tarjim.memory import heavy

    with heavy():
        return shared_engine().transcribe(str(audio))
