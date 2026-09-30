"""The Telegram bot: who it answers, what it accepts, what it sends back."""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim import config
from tarjim.phone import bot as inbox_module
from tarjim.phone import delivery, links, telegram
from tarjim.phone.bot import Inbox, Pairing
from tarjim.phone.progress import Follower
from tarjim.phone.words import say

OWNER, STRANGER = 111, 222


class FakeBot:
    def __init__(self) -> None:
        self.said: list[tuple[int, str]] = []
        self.calls: list[str] = []
        self.keyboards: list[dict[str, Any]] = []

    def say(self, chat: int, text: str, **extra: Any) -> int:
        self.said.append((chat, text))
        if "reply_markup" in extra:
            self.keyboards.append(json.loads(extra["reply_markup"]))
        return len(self.said)

    def edit(self, chat: int, _message: int, text: str, **_extra: Any) -> None:
        self.said.append((chat, text))

    def call(self, method: str, **_params: Any) -> None:
        self.calls.append(method)

    def fetch(self, _file_id: str, target: Path) -> None:
        target.write_bytes(b"video")


class FakeJobs:
    def __init__(self) -> None:
        self.orders: list[Any] = []
        self.steered: list[tuple[str, str]] = []

    def submit(self, order: Any) -> Any:
        self.orders.append(order)
        view = {"title": order.source, "mode": order.mode, "stage": "queued", "paused": False}
        return SimpleNamespace(id="a" * 12, finished=False, view=lambda: view)

    def get(self, _task_id: str) -> None:
        return None

    def steer(self, task_id: str, action: str, _source: str = "") -> None:
        self.steered.append((task_id, action))


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    return tmp_path


def message(chat: int, text: str = "", kind: str = "private", **extra: Any) -> dict[str, Any]:
    return {"message": {"chat": {"id": chat, "type": kind}, "text": text, **extra}}


def setup_inbox(home: Path) -> tuple[Inbox, FakeBot, FakeJobs, Pairing]:
    jobs, pairing = FakeJobs(), Pairing()
    return Inbox(Follower(jobs), home, pairing), FakeBot(), jobs, pairing


def test_only_the_person_with_the_fresh_code_can_pair_and_only_once(home: Path) -> None:
    inbox, bot, _jobs, pairing = setup_inbox(home)
    code = pairing.fresh()
    inbox.handle(bot, message(STRANGER, "/start wrong"))
    assert not config.setting("phone_chat")
    inbox.handle(bot, message(OWNER, f"/start {code}"))
    assert config.setting("phone_chat") == str(OWNER)
    inbox.handle(bot, message(STRANGER, f"/start {code}"))
    assert config.setting("phone_chat") == str(OWNER)
    assert [chat for chat, _ in bot.said] == [STRANGER, OWNER]


def test_an_expired_code_does_not_pair(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox, bot, _jobs, pairing = setup_inbox(home)
    code = pairing.fresh()
    monkeypatch.setattr(inbox_module.time, "time", lambda: pairing.until + 1)
    inbox.handle(bot, message(OWNER, f"/start {code}"))
    assert not config.setting("phone_chat")


def tap(inbox: Inbox, bot: FakeBot, mode: str, chat: int = OWNER) -> None:
    buttons = [b for row in bot.keyboards[-1]["inline_keyboard"] for b in row]
    data = next(b["callback_data"] for b in buttons if b["callback_data"].startswith(f"go:{mode}:"))
    inbox.handle(bot, {"callback_query": {"id": "q", "data": data,
                                          "message": {"chat": {"id": chat}, "message_id": 9}}})


def test_a_link_asks_what_to_make_and_starts_on_the_tap(home: Path) -> None:
    inbox, bot, jobs, _pairing = setup_inbox(home)
    config.save("phone_chat", str(OWNER))
    config.save("phone_mode", "srt")
    config.save("phone_target", "fr")
    inbox.handle(bot, message(STRANGER, "https://youtu.be/abc"))
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc", kind="group"))
    inbox.handle(bot, message(OWNER, "look (https://youtu.be/abc)."))
    assert jobs.orders == [] and len(bot.keyboards) == 1
    first = bot.keyboards[0]["inline_keyboard"][0][0]
    assert first["callback_data"].startswith("go:srt:") and first["text"].startswith("✓")
    tap(inbox, bot, "dub-clone", chat=STRANGER)
    assert jobs.orders == []
    tap(inbox, bot, "dub-clone")
    assert [(o.source, o.mode, o.target) for o in jobs.orders] == [
        ("https://youtu.be/abc", "dub-clone", "fr")]
    assert config.setting("phone_mode") == "dub-clone"
    tap(inbox, bot, "burn")
    assert len(jobs.orders) == 1 and bot.said[-1][1] == say("phone_choice_expired")


def test_a_small_video_is_taken_and_a_large_one_is_refused(home: Path) -> None:
    inbox, bot, jobs, _pairing = setup_inbox(home)
    config.save("phone_chat", str(OWNER))
    small = {"file_id": "f1", "file_size": 1000, "mime_type": "video/mp4", "file_name": "a b.mp4"}
    big = {**small, "file_size": telegram.FETCH_LIMIT + 1}
    inbox.handle(bot, message(OWNER, video=big))
    assert bot.keyboards == []
    inbox.handle(bot, message(OWNER, video=small))
    tap(inbox, bot, "burn")
    assert len(jobs.orders) == 1 and Path(jobs.orders[0].source).read_bytes() == b"video"
    assert Path(jobs.orders[0].source).name == "a_b.mp4"


def test_buttons_change_the_result_or_cancel_only_for_the_owner(home: Path) -> None:
    inbox, bot, jobs, _pairing = setup_inbox(home)
    config.save("phone_chat", str(OWNER))

    def press(chat: int, data: str) -> dict[str, Any]:
        return {"callback_query": {"id": "q", "data": data,
                                   "message": {"chat": {"id": chat}, "message_id": 5}}}

    inbox.handle(bot, press(STRANGER, "mode:srt"))
    assert not config.setting("phone_mode")
    inbox.handle(bot, press(OWNER, "mode:srt"))
    inbox.handle(bot, press(OWNER, "mode:rm -rf"))
    inbox.handle(bot, press(OWNER, f"cancel:{'b' * 12}"))
    assert config.setting("phone_mode") == "srt"
    assert jobs.steered == [("b" * 12, "cancel")]


NAMES = {"x.com": ["104.244.42.1"], "sneaky.example": ["203.0.113.9", "192.168.1.1"]}


@pytest.mark.parametrize(("url", "allowed"), [
    ("https://x.com/a/status/1", True), ("https://x.com./a/status/1", True),
    ("http://127.0.0.1:17653/setup", False), ("http://localhost/x", False),
    ("http://192.168.0.1/admin", False), ("http://[::1]/", False), ("http://router.local/", False),
    ("http://10.0.0.5/v.mp4", False), ("http://sneaky.example/v.mp4", False),
    ("http://unknown.example/v.mp4", False),
])
def test_links_inside_the_home_network_are_never_fetched(
        url: str, allowed: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    real = links.addresses
    monkeypatch.setattr(links, "addresses", lambda host: NAMES.get(host) or (
        real(host) if host[0].isdigit() or ":" in host else []))
    assert links.public(url) is allowed


def test_hidden_links_in_formatted_text_are_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "addresses", lambda _host: ["142.250.1.1"])
    found = {"text": "watch this", "entities": [{"type": "text_link", "url": "https://youtu.be/x"}]}
    assert links.first_link(found) == "https://youtu.be/x"


def test_the_bot_token_never_appears_in_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    token = "123456789:" + "A" * 35

    def refuse(url: str, **_kwargs: Any) -> None:
        raise requests.ConnectionError(f"cannot reach {url}")

    monkeypatch.setattr(requests, "post", refuse)
    with pytest.raises(telegram.TelegramError) as caught:
        telegram.Bot(token).me()
    assert token not in str(caught.value) and caught.value.__cause__ is None


def test_the_file_sent_back_matches_what_was_asked() -> None:
    outputs = [Path("v.ar.dub.mp4"), Path("v.ar.mp4"), Path("v.ar.srt")]
    assert delivery.chosen_output(outputs, "dub-clone") == Path("v.ar.dub.mp4")
    assert delivery.chosen_output(outputs, "burn") == Path("v.ar.mp4")
    assert delivery.chosen_output(outputs, "srt") == Path("v.ar.srt")
    assert delivery.video_kbps(60) > 5000 and delivery.video_kbps(3 * 3600) < 250


class Uploads(FakeBot):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures, self.sent = failures, []

    def send_file(self, _chat: int, path: Path, video: bool) -> None:
        if self.failures:
            self.failures -= 1
            raise telegram.TelegramError("Request Entity Too Large", 413)
        self.sent.append(path.name)


def finished(outputs: list[Path], mode: str) -> Any:
    view = {"title": "clip", "mode": mode, "stage": "done", "paused": False}
    return SimpleNamespace(stage="done", error_code="", outputs=outputs, view=lambda: view,
                           order=SimpleNamespace(mode=mode))


@pytest.mark.parametrize("case", [(2, ["v.ar.mp4"], "phone_sent"),
                                  (3, ["v.ar.srt"], "phone_send_failed")])
def test_each_sending_step_shows_and_a_failed_upload_is_retried_then_reported(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: tuple[int, list[str], str]) -> None:
    from tarjim.phone import sender

    failures, sent, last = case
    monkeypatch.setattr(sender.time, "sleep", lambda _s: None)
    video, subtitles = tmp_path / "v.ar.mp4", tmp_path / "v.ar.srt"
    video.write_bytes(b"x" * 1000)
    subtitles.write_text("1", encoding="utf-8")
    bot = Uploads(failures)
    sender.Sender(bot, OWNER, 7, finished([video, subtitles], "burn")).deliver()  # type: ignore[arg-type]
    shown = [text for _chat, text in bot.said]
    assert bot.sent == sent and shown[-1].endswith(say(last))
    assert any(say("phone_sending", mb=1) in text for text in shown)
