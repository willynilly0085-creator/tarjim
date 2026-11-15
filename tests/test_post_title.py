"""The summary to post is told what the video is called, never who posted it. A link from X is
titled "<the account's name> - <its words>", and on 2026-11-15 a summary began "in a clip by"
that name: the account that shared the clip, which nobody in it says and no reader knows."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import post
from tarjim.job import Job
from tarjim.languages import language
from tarjim.listen.known import ABOUT, called
from tarjim.models import Cue

AR = language("ar")
LINES = [Cue(0.0, 1.0, text="المصنع يعيد تدوير الخردة")]


def linked(folder: Path, title: str, by: str) -> Path:
    video = folder / "clip [123] 720p.mp4"
    kept = {"title": title, "by": by, "description": "posted with a few words"}
    video.with_name(video.name + ABOUT).write_text(json.dumps(kept), encoding="utf-8")
    return video


def test_the_account_that_posted_a_link_is_not_in_what_the_summary_is_told(
        tmp_path: Path) -> None:
    video = linked(tmp_path, "SOME ACCOUNT اسم الحساب - how the plant recycles scrap",
                   "SOME ACCOUNT اسم الحساب")
    assert called(video) == "how the plant recycles scrap"
    asked = post.prompt(called(video), AR, ["المصنع يعيد تدوير الخردة"])
    assert "SOME ACCOUNT" not in asked and "اسم الحساب" not in asked
    assert "Title: how the plant recycles scrap" in asked


def test_a_title_that_does_not_start_with_the_account_is_told_whole(tmp_path: Path) -> None:
    video = linked(tmp_path, "A talk with Jensen Huang - part 2", "Some Channel")
    assert called(video) == "A talk with Jensen Huang - part 2"


def test_a_file_the_person_gave_is_called_by_its_own_name(tmp_path: Path) -> None:
    assert called(tmp_path / "interview with the minister.mp4") == \
        "interview with the minister"


def test_the_summary_is_asked_with_that_title(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[str] = []

    def summary(title: str, *_rest: Any) -> None:
        told.append(title)

    monkeypatch.setattr(post, "summary", summary)
    monkeypatch.setattr(post, "setting", lambda _name: "")
    video = linked(tmp_path, "THE ACCOUNT - its words", "THE ACCOUNT")
    post.write(Job(video, cache_dir=tmp_path / "cache", out_dir=tmp_path), LINES)
    assert told == ["its words"]


def test_the_poster_s_name_is_no_longer_a_reason_to_name_anyone() -> None:
    asked = post.prompt("a title", AR, ["x"])
    assert "file name" not in asked.lower()
    assert "Name a person only when the subtitles or the title name them" in asked
