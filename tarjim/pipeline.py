import json
from dataclasses import dataclass
from pathlib import Path

from tarjim import media
from tarjim.asr.base import Transcript
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
    from tarjim.asr.qwen import QwenEngine

    audio = media.extract_audio(job.video, job.cache / "audio.wav")
    transcript = QwenEngine().transcribe(str(audio))
    transcript.save(cached)
    return transcript


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


def run(job: Job) -> tuple[list[Cue], list[Issue]]:
    cues = build_cues(transcript_for(job).words, cuts_for(job))
    cues = translate(job, cues)
    info = media.probe(job.video)
    ass = job.output(".ass")
    ass.write_text(render_ass(cues, Canvas(info.width, info.height, job.font)), encoding="utf-8")
    job.output(".srt").write_text(render_srt(cues), encoding="utf-8-sig")
    if job.burn:
        burn(job.video, ass, job.output(".mp4"))
    return cues, check(cues)
