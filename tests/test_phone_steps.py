"""The review of 2026-10-29 on the phone bot: an order tarjim cannot make is refused before any
work, a voice needing a key is offered only with it, slow steps never hold up the next message,
and the same link sent twice leaves no frozen message behind."""
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim import config, fetch
from tarjim.phone import choice, links
from tarjim.phone.bot import Inbox, Pairing
from tarjim.phone.progress import Follower
from tarjim.phone.words import say
from tests.test_phone import OWNER, FakeBot, FakeJobs, message, pick, setup_inbox, tap


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(links, "addresses", lambda _host: ["142.250.1.1"])
    monkeypatch.setattr(fetch, "look", lambda _url: {"choices": [], "default": "", "audio": None,
                                                     "limit": 8 * 1024 ** 3, "title": ""})
    config.save("phone_chat", str(OWNER))
    return tmp_path


def test_a_dub_the_language_has_no_voice_for_is_refused_before_any_work(home: Path) -> None:
    inbox, bot, jobs, _pairing = setup_inbox(home)
    config.save("phone_target", "ur")
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    tap(inbox, bot, "dub-clone")
    assert jobs.orders == []
    assert bot.said[-1][1] == say("sendDubLanguage", language="اردو")


def test_a_video_sent_for_a_dub_that_cannot_be_made_is_never_downloaded(home: Path) -> None:
    class Counting(FakeBot):
        fetched = 0

        def fetch(self, _file_id: str, target: Path, tell: Any = None) -> None:
            self.fetched += 1

    inbox, _bot, jobs, _pairing = setup_inbox(home)
    bot = Counting()
    config.save("phone_target", "ur")
    video = {"file_id": "f1", "file_size": 1000, "mime_type": "video/mp4"}
    inbox.handle(bot, message(OWNER, video=video))
    tap(inbox, bot, "dub-clone")
    assert bot.fetched == 0 and jobs.orders == []


def test_the_natural_voice_is_offered_only_with_a_gemini_key(home: Path) -> None:
    assert "dub-gemini" not in choice.offered() and "dub-gemini" in choice.MODES
    config.save(config.GEMINI, "AIza" + "k" * 35)
    assert choice.offered()[:5] == ["burn", "srt", "dub-gemini", "dub-clone", "dub-studio"]


def test_a_slow_quality_list_does_not_hold_up_a_cancel(home: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    release, asked = threading.Event(), threading.Event()

    def slow(_url: str) -> Any:
        asked.set()
        release.wait(5)
        raise RuntimeError("yt-dlp gave up")

    monkeypatch.setattr(fetch, "look", slow)
    jobs, bot = FakeJobs(), FakeBot()
    inbox = Inbox(Follower(jobs), home, Pairing())  # the real worker, not the tests' inline one
    config.save("phone_target", "fr")
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    pick(inbox, bot, "go:burn:")
    assert asked.wait(5)
    inbox.handle(bot, {"callback_query": {"id": "q", "data": f"cancel:{'b' * 12}",
                                          "message": {"chat": {"id": OWNER}, "message_id": 4}}})
    assert jobs.steered == [("b" * 12, "cancel")] and jobs.orders == []
    release.set()
    for _ in range(50):
        if jobs.orders:
            break
        threading.Event().wait(0.05)
    assert [o.mode for o in jobs.orders] == ["burn"]


def test_the_same_link_twice_moves_its_progress_to_the_newer_message() -> None:
    edits: list[tuple[int, str, bool]] = []

    class Watching(FakeBot):
        def edit(self, chat: int, message: int, text: str, **extra: Any) -> None:
            edits.append((message, text, "reply_markup" in extra))

    task = SimpleNamespace(id="c" * 12, stage="queued", finished=False, moved=(0, 0),
                           view=lambda: {"title": "t", "mode": "burn", "stage": "queued",
                                         "paused": False, "link": True, "created": 0.0},
                           order=SimpleNamespace(mode="burn"))
    follower = Follower(FakeJobs())
    follower.adopt(Watching(), OWNER, 5, task)  # type: ignore[arg-type]
    follower.adopt(Watching(), OWNER, 8, task)  # type: ignore[arg-type]
    assert follower.watching[task.id].message == 8
    assert (5, say("phone_same_job"), False) in edits  # no Cancel left on the old message
