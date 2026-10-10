"""The person sees how far every transfer is: a small video coming in, a result going back, and
a link being downloaded on the computer."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import requests

from tarjim import fetch, job
from tarjim.phone import meter, telegram
from tarjim.phone.progress import Watch, status_text
from tarjim.phone.upload import Body
from tarjim.phone.words import say

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def every_step_is_told(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meter, "EVERY", 0.0)


def test_a_small_video_coming_in_tells_how_far_it_is(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = b"x" * (3 * MB)

    class Reply:
        status_code = 206

        def __enter__(self) -> "Reply":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def iter_content(self, _size: int) -> Any:
            yield body[:MB]
            yield body[MB:]

    monkeypatch.setattr(requests, "get", lambda *_a, **_k: Reply())
    monkeypatch.setattr(telegram.Bot, "call",
                        lambda *_a, **_k: {"file_path": "v.mp4", "file_size": len(body)})
    told: list[tuple[int, int]] = []
    telegram.Bot("t").fetch("f1", tmp_path / "v.mp4", lambda *far: told.append(far))
    assert told == [(1, 3), (3, 3)] and (tmp_path / "v.mp4").stat().st_size == len(body)


def test_a_result_going_back_is_read_from_disk_and_tells_how_far_it_is(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = tmp_path / "clip final.mp4"
    video.write_bytes(b"v" * (2 * MB))
    seen: dict[str, Any] = {}

    def post(url: str, data: Body, headers: dict[str, str], **_kwargs: Any) -> Any:
        sent = b""
        while piece := data.read(8192):
            sent += piece
        seen.update(sent=sent, length=len(data), kind=headers["Content-Type"])
        return SimpleNamespace(headers={"content-type": "application/json"}, status_code=200,
                               json=lambda: {"ok": True, "result": {}})

    monkeypatch.setattr(requests, "post", post)
    told: list[tuple[int, int]] = []
    telegram.Bot("t").send_file(7, video, True, lambda done, total: told.append((done, total)))
    assert len(seen["sent"]) == seen["length"] and seen["kind"].startswith("multipart/form-data")
    assert b'name="chat_id"\r\n\r\n7\r\n' in seen["sent"] and b"v" * (2 * MB) in seen["sent"]
    assert b'filename="clip final.mp4"' in seen["sent"] and told[-1] == (2, 2)


def test_a_link_being_downloaded_shows_its_bar_in_the_checklist() -> None:
    moved: list[tuple[int, int]] = []
    token = job.PROGRESS.set(lambda done, total: moved.append((done, total)))
    fetch.told({"downloaded_bytes": 12 * MB, "total_bytes_estimate": 48 * MB})
    job.PROGRESS.reset(token)
    assert moved == [(12 * MB, 48 * MB)]
    view = {"title": "clip", "mode": "burn", "stage": "downloading", "paused": False,
            "link": True, "created": 0.0}
    task = SimpleNamespace(stage="downloading", moved=moved[0], view=lambda: view)
    text = status_text(task, Watch(1, 2))
    assert f"● {say('stage_downloading')} ({meter.amount(12, 48)})" in text
    task.stage = view["stage"] = "hearing"
    assert meter.bar(12, 48) not in status_text(task, Watch(1, 2))
