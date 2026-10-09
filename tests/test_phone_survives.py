"""The phone bot keeps answering after a surprise, and a started job is never lost from view."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import requests
from test_phone import OWNER, FakeBot, FakeJobs

from tarjim import config
from tarjim.phone import service as service_module
from tarjim.phone import telegram
from tarjim.phone.bot import Pairing
from tarjim.phone.progress import Follower, deliver
from tarjim.phone.service import Service
from tarjim.phone.words import say


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def test_a_pairing_code_in_any_alphabet_is_just_wrong() -> None:
    pairing = Pairing()
    code = pairing.fresh()
    assert not pairing.take("é") and pairing.take(code)


class Deaf(FakeBot):
    def edit(self, _chat: int, _message: int, _text: str, **_extra: Any) -> None:
        raise telegram.TelegramError("Too Many Requests", 429)


def test_a_job_is_followed_even_when_its_first_message_cannot_be_shown() -> None:
    follower = Follower(FakeJobs())
    task = FakeJobs().submit(SimpleNamespace(source="s", mode="burn"))
    follower.adopt(Deaf(), OWNER, 9, task)  # type: ignore[arg-type]
    assert task.id in follower.watching


def test_a_reply_that_is_not_json_is_a_telegram_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: Any, **_kwargs: Any) -> Any:
        def unreadable() -> Any:
            raise ValueError("Expecting value")
        return SimpleNamespace(headers={"content-type": "application/json"}, status_code=502,
                               json=unreadable)

    monkeypatch.setattr(requests, "post", broken)
    with pytest.raises(telegram.TelegramError):
        telegram.Bot("t").me()


class Surprising:
    def __init__(self, service: Service) -> None:
        self.service, self.asked = service, 0

    def updates(self, _offset: int) -> list[dict[str, Any]]:
        self.asked += 1
        if self.asked == 1:
            raise ValueError("a surprise")
        self.service.stop.set()
        return [{"update_id": 7, "message": {"chat": {"id": 1, "type": "private"}}}]


def test_reading_messages_goes_on_after_a_surprise(monkeypatch: pytest.MonkeyPatch) -> None:
    service = Service()
    bot = Surprising(service)
    handled: list[int] = []

    def explode(_bot: Any, update: dict[str, Any]) -> None:
        handled.append(update["update_id"])
        raise TypeError("another surprise")

    monkeypatch.setattr(service_module, "RETRY", (0,))
    monkeypatch.setattr(service, "bot", lambda: bot)
    service.inbox = SimpleNamespace(handle=explode)  # type: ignore[assignment]
    service.poll()
    assert bot.asked == 2 and handled == [7] and config.setting("phone_offset") == "8"


def test_a_file_that_arrived_whole_before_the_line_dropped_is_kept(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body, asked = b"whole video", []

    class Dropped:
        status_code = 206

        def __enter__(self) -> "Dropped":
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def iter_content(self, _size: int) -> Any:
            yield body
            raise requests.ConnectionError("dropped at the end")

    def get(_url: str, **_kwargs: Any) -> Dropped:
        asked.append(1)
        return Dropped()

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(telegram.Bot, "call",
                        lambda *_a, **_k: {"file_path": "v.mp4", "file_size": len(body)})
    telegram.Bot("t").fetch("f1", tmp_path / "v.mp4")
    assert (tmp_path / "v.mp4").read_bytes() == body and len(asked) == 1


def test_a_result_that_cannot_be_prepared_is_reported_to_the_phone(tmp_path: Path) -> None:
    bot = FakeBot()
    missing = tmp_path / "gone.ar.mp4"
    task = SimpleNamespace(stage="done", outputs=[missing], order=SimpleNamespace(mode="burn"),
                           error_code="", view=lambda: {"title": "clip", "mode": "burn",
                                                        "stage": "done", "paused": False,
                                                        "link": True, "created": 0.0})
    deliver(bot, SimpleNamespace(chat=OWNER, message=9), task)  # type: ignore[arg-type]
    assert bot.said[-1] == (OWNER, say("phone_send_failed"))
