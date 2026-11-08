"""What filled speech left out is kept with the hearing, judged again against the lines chosen on
each later run, and kept before any timing starts (2026-11-08)."""
import json
from pathlib import Path
from typing import Any

import pytest
from test_coverage_flow import LOCAL, SPOKEN, Engine, setup

from tarjim import config, hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import timing
from tarjim.models import Word


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def spoken_once(transcript: Transcript) -> bool:
    """Every word said in the clip, each of them once."""
    return sorted(w.text for w in transcript.words) == sorted(w.text for w in LOCAL)


def dropped_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                local: list[Word] | None) -> tuple[Job, Engine]:
    """A clip whose hearing stopped at 160 s, heard and mended once."""
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine, local)
    hearing.transcript_for(job, lambda _stage: None)
    return job, engine


def voted_whole(job: Job, old_format: bool) -> None:
    """The kept hearing as a later release votes it: the ending is among the lines chosen now."""
    path = job.cache / "heard.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["utterances"] = [vars(u) for u in SPOKEN]
    data["passes"] = [data["utterances"]]
    if old_format:  # kept before 2026-11-08: bare lines, with no stretch
        data["added"] = [fill["line"] for fill in data["added"]]
    path.write_text(json.dumps(data), encoding="utf-8")
    (job.cache / "transcript.json").unlink()


@pytest.mark.parametrize("old_format", [False, True], ids=["with stretch", "bare line"])
@pytest.mark.parametrize("local", [LOCAL, None], ids=["local words", "no local listener"])
def test_a_kept_fill_the_lines_chosen_now_say_is_left_out(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, old_format: bool,
        local: list[Word] | None) -> None:
    job, engine = dropped_end(monkeypatch, tmp_path, local)
    voted_whole(job, old_format)
    assert spoken_once(hearing.transcript_for(job, lambda _stage: None))
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert kept["added"] == [] and engine.asked == 1


@pytest.mark.parametrize("local", [LOCAL, None], ids=["local words", "no local listener"])
def test_a_kept_fill_stays_while_its_stretch_is_still_left_out(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local: list[Word] | None) -> None:
    job, engine = dropped_end(monkeypatch, tmp_path, local)
    (job.cache / "transcript.json").unlink()
    assert spoken_once(hearing.transcript_for(job, lambda _stage: None))
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert len(kept["added"]) == 13 and engine.asked == 1


def test_the_hearing_is_kept_before_a_timing_that_never_ends(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine)
    listened: list[int] = []

    def listen(video: Path, audio: Path) -> Any:
        listened.append(1)
        return engine.listen_video(video, audio)

    whole, broke = timing.Timer.whole, [False]

    def dies_once(self: timing.Timer, utterances: Any) -> list[Word]:
        if not broke[0]:
            broke[0] = True
            raise MemoryError("the aligner ran out of memory")
        return whole(self, utterances)

    monkeypatch.setattr(hearing, "listen_video", listen)
    monkeypatch.setattr(timing.Timer, "whole", dies_once)
    with pytest.raises(MemoryError):
        hearing.transcript_for(job, lambda _stage: None)
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert len(kept["added"]) == 13 and (job.cache / "asked.json").exists()
    assert spoken_once(hearing.transcript_for(job, lambda _stage: None))
    assert listened == [1] and engine.asked == 1
