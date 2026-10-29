import json
from collections.abc import Callable
from pathlib import Path

from tarjim import media
from tarjim.hearing import transcript_for
from tarjim.job import Job, checkpoint
from tarjim.models import Cue, Word
from tarjim.qa import Issue, check
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.burn import burn
from tarjim.render.mark import Mark, mark_for
from tarjim.render.placement import placed
from tarjim.render.srt import render_srt
from tarjim.segment import build_cues

Report = Callable[[str], None]


def first_failure(failures: list[Exception]) -> RuntimeError:
    """The engine the person chose explains the failure, not the backup tried after it."""
    if not failures:
        return RuntimeError("no translation engine")
    first = failures[0]
    return first if isinstance(first, RuntimeError) else RuntimeError(
        f"translation reply could not be read: {first!r}")


def quiet(_stage: str) -> None:
    return None


def cuts_for(job: Job) -> list[float]:
    cached = job.cache / "cuts.json"
    if cached.exists():
        return list(json.loads(cached.read_text(encoding="utf-8")))
    cuts = media.scene_cuts(job.video)
    if cuts is None:
        return []
    cached.write_text(json.dumps(cuts), encoding="utf-8")
    return cuts


def translate(job: Job, cues: list[Cue]) -> list[Cue]:
    from tarjim.engines.choice import asker, chain
    from tarjim.translate.gemini import BAD_REPLY, Translator
    from tarjim.translate.prompt import Brief

    def audio(start: float, end: float) -> bytes:
        return media.audio_bytes(job.video, start, end)

    from tarjim.translate.glossary import current

    brief = Brief(job.language, job.dialect, job.rules, glossary=current(job.target))
    failures: list[Exception] = []
    for provider in chain("translate"):
        checkpoint()  # a backup engine is never started for a job that was cancelled
        left = [cue for cue in cues if not cue.text.strip()]  # a backup never redoes good lines
        try:
            Translator(asker(provider)).translate(left, audio, brief)
            return cues
        except BAD_REPLY as error:
            failures.append(error)
    raise first_failure(failures)


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
    canvas = placed(job, cues, Canvas(info.width, info.height, job.font_name,
                                      media.bright_bottom(job.video)), info.duration)
    subtitles = render_ass(cues, canvas, job.rules)
    job.output(".ass").write_text(subtitles, encoding="utf-8")
    mark = mark_for(canvas)
    if job.burn:
        report("burning")
        burn(job.video, subtitles, job.output(".mp4"), mark)
    if job.dub:
        from tarjim.dub.make import dub_video

        report("dubbing")
        dub_video(job, cues, words, picture_for(job, canvas, mark))


def picture_for(job: Job, canvas: Canvas, mark: Mark | None) -> Path:
    """What a dub is laid on: the burned video, or the source with only the mark drawn on it."""
    if job.burn:
        return job.output(".mp4")
    if mark is None:
        return job.video
    return burn(job.video, render_ass([], canvas, job.rules), job.cache / "marked.mp4", mark)


def run(job: Job, report: Report = quiet) -> tuple[list[Cue], list[Issue]]:
    job.claim_cache()
    media.check_readable(job.video)
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
