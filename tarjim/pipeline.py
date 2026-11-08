import json
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from tarjim import guards, media
from tarjim.findings import findings
from tarjim.hearing import transcript_for
from tarjim.job import Job
from tarjim.models import Cue, Word
from tarjim.qa import Issue, check
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.burn import burn
from tarjim.render.mark import Mark, mark_for
from tarjim.render.moments import moved
from tarjim.render.placement import placed
from tarjim.render.room import fitted
from tarjim.render.srt import render_srt
from tarjim.rules import Rules
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


def translate(job: Job, cues: list[Cue], rules: Rules | None = None) -> list[Cue]:
    """Every engine of the chain while a line is untranslated (translate/rounds.py). The job
    fails only when no engine translated anything; otherwise what they did is kept, and why an
    engine stopped is kept on the job beside the lines left as said."""
    from tarjim.translate.glossary import current
    from tarjim.translate.prompt import Brief
    from tarjim.translate.rounds import Rounds

    def audio(start: float, end: float) -> bytes:
        return media.audio_bytes(job.video, start, end)

    shaped = rules or job.rules
    brief = Brief(job.language, job.dialect, shaped, glossary=current(job.target))
    rounds = Rounds(cues, audio, brief)
    failures = rounds.run()
    if failures and not rounds.translated():
        raise first_failure(failures)
    rounds.finish(shaped)
    # Since 2026-11-08 only the last engine that ran explains the lines left as said: a line a
    # backup left out without failing is listed as such (in_source), not blamed on the quota of
    # the engine before it.
    if rounds.stopped:
        findings().stopped = first_failure(rounds.stopped)
    return cues


def save_review(job: Job, cues: list[Cue]) -> None:
    rows = [{"start": round(c.start, 2), "end": round(c.end, 2), "source": c.source,
             "text": c.text} for c in cues]
    review = job.cache / f"cues.{job.target}.json"
    review.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


class Made(NamedTuple):
    """What the outputs are written from: the subtitles, the words heard (a dub is timed by
    them) and the picture, probed once a run, with the rules fitted to it (2026-11-08)."""
    cues: list[Cue]
    words: list[Word]
    info: media.VideoInfo
    rules: Rules | None = None


def write_outputs(job: Job, made: Made, report: Report) -> None:
    cues = made.cues
    # the rules fitted to the picture, as the .ass, the translation and the check use: before
    # 2026-11-08 the .srt was wrapped by the unfitted ones and broke its lines differently
    rules = made.rules or fitted(job.rules, made.info.width, made.info.height)
    job.output(".srt").write_text(render_srt(cues, rules), encoding="utf-8-sig")
    picture = write_picture(job, cues, made.info, report)
    if job.dub:
        from tarjim.dub.make import dub_video

        report("dubbing")
        dub_video(job, cues, made.words, picture)  # no picture: the sound alone is dubbed


def write_picture(job: Job, cues: list[Cue], info: media.VideoInfo,
                  report: Report) -> Path | None:
    """The subtitles drawn for the picture, burned when asked; what a dub is laid on, or None
    for a file with no picture."""
    if not info.has_picture:
        return None
    canvas = placed(job, cues, Canvas(info.width, info.height, job.font_name), info.duration)
    mark = mark_for(canvas)
    canvas = moved(job, cues, canvas, mark)
    subtitles = render_ass(cues, canvas, fitted(job.rules, canvas.width, canvas.height))
    job.output(".ass").write_text(subtitles, encoding="utf-8")
    if job.burn:
        report("burning")
        burn(job.video, subtitles, job.output(".mp4"), mark)
    return picture_for(job, canvas, mark) if job.dub else None


def picture_for(job: Job, canvas: Canvas, mark: Mark | None) -> Path:
    """What a dub is laid on: the burned video, or the source with only the mark drawn on it."""
    if job.burn:
        return job.output(".mp4")
    if mark is None:
        return job.video
    return burn(job.video, render_ass([], canvas, job.rules), job.cache / "marked.mp4", mark)


def run(job: Job, report: Report = quiet) -> tuple[list[Cue], list[Issue]]:
    guards.reset()  # each job counts from nothing, the command line's too (2026-11-08)
    job.claim_cache()
    media.check_readable(job.video)
    report("hearing")
    words = transcript_for(job, report).words
    findings().guarded()  # once per job, when every guard has had its say (2026-11-08)
    info = media.probe(job.video)
    # the target language's rules, its lines shortened for the picture's shape: before
    # 2026-11-08 the cues were cut by the default rules whatever the language
    rules = fitted(job.rules, info.width, info.height)
    cues = build_cues(words, cuts_for(job), rules)
    report("translating")
    cues = translate(job, cues, rules)
    save_review(job, cues)
    report("writing")
    write_outputs(job, Made(cues, words, info, rules), report)
    report("done")
    return cues, check(cues, rules)
