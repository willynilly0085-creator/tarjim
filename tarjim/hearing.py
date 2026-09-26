import json
from dataclasses import asdict
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word

Regions = list[tuple[float, float]]


def transcript_for(job: Job) -> Transcript:
    cached = job.cache / "transcript.json"
    if cached.exists():
        return Transcript.load(cached)
    audio = media.extract_audio(job.video, job.cache / "audio.wav")
    transcript = listen_and_align(job, audio) or qwen_transcript(audio)
    transcript.save(cached)
    return transcript


def heard_for(job: Job, audio: Path) -> tuple[str, list[Utterance]]:
    cached = job.cache / "heard.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return data["language"], [Utterance(**u) for u in data["utterances"]]
    heard = listen_video(job.video, audio)
    payload = {"language": heard.language, "utterances": [asdict(u) for u in heard.utterances],
               "passes": [[asdict(u) for u in run] for run in heard.passes]}
    cached.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return heard.language, heard.utterances


def listen_video(video: Path, audio: Path) -> Heard:
    from tarjim.listen.chunks import is_long, listen_in_chunks
    from tarjim.listen.gemini_listen import listen
    from tarjim.listen.merge import listen_many

    duration = media.probe(video).duration

    def listen_span(start: float, end: float) -> Heard:
        sound = media.audio_bytes(video, start, end if end > start else None)
        return listen_many(lambda: listen(sound))

    regions = speech_regions_of(audio) if is_long(duration) else []
    return listen_in_chunks(duration, regions, listen_span)


def speech_regions_of(audio: Path) -> Regions:
    import soundfile

    from tarjim.asr.vad import speech_regions

    wav, _ = soundfile.read(str(audio), dtype="float32")
    return speech_regions(wav)


def listen_and_align(job: Job, audio: Path) -> Transcript | None:
    import soundfile

    from tarjim.asr.align import AlignEngine
    from tarjim.asr.fuse import fuse

    try:
        language, utterances = heard_for(job, audio)
    except RuntimeError:
        return None
    if not utterances:
        return None
    wav, _ = soundfile.read(str(audio), dtype="float32")
    words = AlignEngine().align(wav, utterances, language)
    words = fuse(words, utterances, second_opinion(audio))
    return Transcript(language=language, text=" ".join(u.text for u in utterances), words=words)


def second_opinion(audio: Path) -> list[Word]:
    try:
        return qwen_transcript(audio).words
    except (RuntimeError, ValueError, MemoryError):
        return []


def qwen_transcript(audio: Path) -> Transcript:
    from tarjim.asr.qwen import QwenEngine

    return QwenEngine().transcribe(str(audio))
