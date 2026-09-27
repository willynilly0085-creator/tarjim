import json
from collections.abc import Callable

from tarjim import media
from tarjim.hearing import transcript_for
from tarjim.job import Job
from tarjim.models import Cue, Word
from tarjim.qa import Issue, check
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.burn import burn
from tarjim.render.srt import render_srt
from tarjim.segment import build_cues

Report = Callable[[str], None]


def quiet(_stage: str) -> None:
    return None


def cuts_for(job: Job) -> list[float]:
    cached = job.cache / "cuts.json"
    if cached.exists():
        return list(json.loads(cached.read_text(encoding="utf-8")))
    cuts = media.scene_cuts(job.video)
    cached.write_text(json.dumps(cuts), encoding="utf-8")
    return cuts


def translate(job: Job, cues: list[Cue]) -> list[Cue]:
    from tarjim.engines.choice import asker, chain
    from tarjim.translate.gemini import Translator
    from tarjim.translate.prompt import Brief

    def audio(start: float, end: float) -> bytes:
        return media.audio_bytes(job.video, start, end)

    from tarjim.translate.glossary import current

    brief = Brief(job.language, job.dialect, job.rules, glossary=current())
    failures: list[Exception] = []
    for provider in chain("translate"):
        try:
            return Translator(asker(provider)).translate(cues, audio, brief)
        except RuntimeError as error:
            failures.append(error)
    raise failures[-1] if failures else RuntimeError("no translation engine")


def save_review(job: Job, cues: list[Cue]) -> None:
    rows = [{"start": round(c.start, 2), "end": round(c.end, 2), "source": c.source,
             "text": c.text} for c in cues]
    review = job.cache / f"cues.{job.target}.json"
    review.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def write_outputs(job: Job, cues: list[Cue], words: list[Word], report: Report) -> None:
    job.output(".srt").write_text(render_srt(cues, job.rules), encoding="utf-8-sig")
    info = media.probe(job.video)
    if not info.has_picture:
        return
    ass = job.output(".ass")
    canvas = Canvas(info.width, info.height, job.font_name, media.bright_bottom(job.video))
    ass.write_text(render_ass(cues, canvas, job.rules), encoding="utf-8")
    if job.burn:
        report("burning")
        burn(job.video, ass, job.output(".mp4"))
    if job.dub:
        from tarjim.dub.make import dub_video

        report("dubbing")
        picture = job.output(".mp4") if job.burn else job.video
        dub_video(job, cues, words, picture)


def run(job: Job, report: Report = quiet) -> tuple[list[Cue], list[Issue]]:
    report("hearing")
    words = transcript_for(job, report).words
    cues = build_cues(words, cuts_for(job))
    report("translating")
    cues = translate(job, cues)
    save_review(job, cues)
    report("writing")
    write_outputs(job, cues, words, report)
    report("done")
    return cues, check(cues, job.rules)
