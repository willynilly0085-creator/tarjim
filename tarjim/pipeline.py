import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Cue
from tarjim.qa import Issue, check
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.burn import burn
from tarjim.render.srt import render_srt
from tarjim.segment import build_cues


@dataclass(frozen=True)
class Job:
    video: Path
    dialect: str = "saudi"
    burn: bool = True
    font: str = "Dubai"

    @property
    def cache(self) -> Path:
        folder = self.video.parent / ".tarjim" / self.video.stem
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def output(self, suffix: str) -> Path:
        return self.video.with_name(f"{self.video.stem}.ar{suffix}")


def transcript_for(job: Job) -> Transcript:
    cached = job.cache / "transcript.json"
    if cached.exists():
        return Transcript.load(cached)
    audio = media.extract_audio(job.video, job.cache / "audio.wav")
    transcript = listen_and_align(job, audio) or qwen_transcript(audio)
    transcript.save(cached)
    return transcript


def heard_for(job: Job) -> tuple[str, list[Utterance]]:
    from tarjim.listen.gemini_listen import listen
    from tarjim.listen.merge import listen_many

    cached = job.cache / "heard.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return data["language"], [Utterance(**u) for u in data["utterances"]]
    sound = media.audio_bytes(job.video)
    heard = listen_many(lambda: listen(sound))
    payload = {"language": heard.language, "utterances": [asdict(u) for u in heard.utterances],
               "passes": [[asdict(u) for u in run] for run in heard.passes]}
    cached.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return heard.language, heard.utterances


def listen_and_align(job: Job, audio: Path) -> Transcript | None:
    import soundfile

    from tarjim.asr.align import AlignEngine
    from tarjim.asr.fuse import fuse

    try:
        language, utterances = heard_for(job)
    except RuntimeError:
        return None
    if not utterances:
        return None
    wav, _ = soundfile.read(str(audio), dtype="float32")
    words = AlignEngine().align(wav, utterances, language)
    words = fuse(words, utterances, qwen_transcript(audio).words)
    return Transcript(language=language, text=" ".join(u.text for u in utterances), words=words)


def qwen_transcript(audio: Path) -> Transcript:
    from tarjim.asr.qwen import QwenEngine

    return QwenEngine().transcribe(str(audio))


def cuts_for(job: Job) -> list[float]:
    cached = job.cache / "cuts.json"
    if cached.exists():
        return list(json.loads(cached.read_text(encoding="utf-8")))
    cuts = media.scene_cuts(job.video)
    cached.write_text(json.dumps(cuts), encoding="utf-8")
    return cuts


def translate(job: Job, cues: list[Cue]) -> list[Cue]:
    from tarjim.translate.gemini import GeminiTranslator

    return GeminiTranslator().translate(cues, media.audio_bytes(job.video), job.dialect)


def save_review(job: Job, cues: list[Cue]) -> None:
    rows = [{"start": round(c.start, 2), "end": round(c.end, 2), "source": c.source,
             "text": c.text} for c in cues]
    review = job.cache / "cues.json"
    review.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def run(job: Job) -> tuple[list[Cue], list[Issue]]:
    cues = build_cues(transcript_for(job).words, cuts_for(job))
    cues = translate(job, cues)
    save_review(job, cues)
    info = media.probe(job.video)
    ass = job.output(".ass")
    ass.write_text(render_ass(cues, Canvas(info.width, info.height, job.font)), encoding="utf-8")
    job.output(".srt").write_text(render_srt(cues), encoding="utf-8-sig")
    if job.burn:
        burn(job.video, ass, job.output(".mp4"))
    return cues, check(cues)
