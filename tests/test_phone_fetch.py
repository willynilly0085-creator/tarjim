"""Taking a video out of Telegram over a line that drops in the middle."""
from pathlib import Path
from typing import Any

import pytest
import requests
from test_phone import OWNER, FakeBot, message, setup_inbox, tap

from tarjim import config
from tarjim.phone import telegram
from tarjim.phone.words import say

VIDEO = bytes(range(200)) * 5


class Reply:
    def __init__(self, body: bytes, drop_after: int) -> None:
        self.body, self.drop_after, self.status_code = body, drop_after, 206

    def __enter__(self) -> "Reply":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def iter_content(self, _size: int) -> Any:
        yield self.body[:self.drop_after]
        if self.drop_after < len(self.body):
            raise requests.ConnectionError("read timed out")


def line(monkeypatch: pytest.MonkeyPatch, drop_after: int) -> list[str]:
    """A file server that honours Range and drops every connection after a few bytes."""
    asked: list[str] = []

    def get(_url: str, headers: dict[str, str], **_kwargs: Any) -> Reply:
        asked.append(headers["Range"])
        start = int(headers["Range"].removeprefix("bytes=").rstrip("-"))
        return Reply(VIDEO[start:], drop_after)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(telegram.Bot, "call", lambda *_a, **_k: {"file_path": "videos/f.mp4"})
    return asked


def test_a_download_that_drops_midway_continues_from_where_it_stopped(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = line(monkeypatch, drop_after=300)
    telegram.Bot("t").fetch("f1", tmp_path / "v.mp4")
    assert (tmp_path / "v.mp4").read_bytes() == VIDEO
    assert asked == ["bytes=0-", "bytes=300-", "bytes=600-", "bytes=900-"]


def test_a_download_that_never_moves_gives_up_and_leaves_no_half_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = line(monkeypatch, drop_after=0)
    with pytest.raises(telegram.TelegramError):
        telegram.Bot("t").fetch("f1", tmp_path / "v.mp4")
    assert len(asked) == telegram.STALLS and not (tmp_path / "v.mp4").exists()


class Unreachable(FakeBot):
    def fetch(self, _file_id: str, target: Path) -> None:
        raise telegram.TelegramError("download stalled")


def test_the_person_is_told_when_the_video_cannot_be_taken(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    inbox, _bot, jobs, _pairing = setup_inbox(tmp_path)
    bot = Unreachable()
    config.save("phone_chat", str(OWNER))
    video = {"file_id": "f1", "file_size": 1000, "mime_type": "video/mp4"}
    inbox.handle(bot, message(OWNER, video=video))
    tap(inbox, bot, "burn")
    assert jobs.orders == [] and [text for _chat, text in bot.said[-2:]] == [
        say("stage_downloading"), say("phone_fetch_failed")]
