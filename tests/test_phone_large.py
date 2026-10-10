"""Videos over the Bot API's limits go in and come back through the app protocol, once the person
has saved Telegram's app id and hash."""
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_phone import OWNER, FakeBot, message, setup_inbox, tap

from tarjim import config
from tarjim.phone import large, sender, telegram
from tarjim.phone.words import say

MB = 1024 * 1024
BIG = {"file_id": "f1", "file_size": 300 * MB, "mime_type": "video/mp4", "file_name": "long.mp4"}


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    config.save("phone_chat", str(OWNER))
    return tmp_path


def turn_on() -> None:
    config.save("telegram_token", "123456789:" + "A" * 35)
    config.save("telegram_api_id", "1234567")
    config.save("telegram_api_hash", "0123456789abcdef" * 2)


def test_large_files_need_a_well_formed_id_and_hash() -> None:
    assert not large.ready()
    turn_on()
    assert large.ready() and large.well_formed("1234567", "ab" * 16)
    assert not large.well_formed("12", "ab" * 16) and not large.well_formed("1234567", "XYZ")


def test_a_big_video_is_refused_until_large_files_are_on_and_names_the_way(home: Path) -> None:
    inbox, bot, jobs, _pairing = setup_inbox(home)
    inbox.handle(bot, message(OWNER, video=BIG, message_id=77))
    assert bot.keyboards == [] and bot.said[-1] == (OWNER, say("phone_file_big"))
    turn_on()
    inbox.handle(bot, message(OWNER, video={**BIG, "file_size": large.LIMIT + 1}, message_id=78))
    assert bot.keyboards == [] and bot.said[-1] == (OWNER, say("phone_file_huge"))
    assert jobs.orders == []


def test_a_big_video_is_taken_through_the_app_protocol_by_its_message(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    taken: list[tuple[int, int]] = []

    def fetch(chat: int, message_id: int, target: Path, tell: Any) -> None:
        taken.append((chat, message_id))
        tell(47, 120)
        target.write_bytes(b"big video")

    turn_on()
    monkeypatch.setattr(large, "fetch", fetch)
    inbox, bot, jobs, _pairing = setup_inbox(home)
    inbox.handle(bot, message(OWNER, video=BIG, message_id=77))
    tap(inbox, bot, "burn")
    assert taken == [(OWNER, 77)] and Path(jobs.orders[0].source).read_bytes() == b"big video"
    shown = [text for _chat, text in bot.said]
    bar = "▰▰▰▰▱▱▱▱▱▱"
    progress = f"{bar} {say('phone_progress', done=47, total=120)}"
    assert "\n".join((say("stage_downloading"), progress)) in shown
    assert large.bar(0, 120) == "▱" * 10 and large.bar(120, 120) == "▰" * 10


def test_progress_is_told_in_megabytes_and_not_too_often(monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[tuple[int, int]] = []
    clock = iter([100.0, 100.0, 101.0, 105.0, 105.0])
    monkeypatch.setattr(large.time, "monotonic", lambda: next(clock))
    meter = large.Meter(lambda done, total: told.append((done, total)))
    for done in (10 * MB, 20 * MB, 60 * MB):
        meter(done, 120 * MB)
    assert told == [(10, 120), (60, 120)]


class Uploads(FakeBot):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []

    def send_file(self, _chat: int, path: Path, video: bool) -> None:
        self.sent.append(path.name)


def finished(video: Path) -> Any:
    view = {"title": "clip", "mode": "burn", "stage": "done", "paused": False, "link": False,
            "created": 0.0}
    return SimpleNamespace(stage="done", error_code="", outputs=[video], view=lambda: view,
                           order=SimpleNamespace(mode="burn"))


def test_the_result_goes_back_whole_when_large_files_are_on(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = tmp_path / "v.ar.mp4"
    video.write_bytes(b"x" * 1000)
    monkeypatch.setattr(sender, "SEND_LIMIT", 100)
    whole: list[tuple[int, str]] = []
    monkeypatch.setattr(large, "send", lambda chat, path, _tell: whole.append((chat, path.name)))
    monkeypatch.setattr(sender, "phone_copy", lambda _path: pytest.fail("no smaller copy"))
    turn_on()
    bot = Uploads()
    sender.Sender(bot, OWNER, 7, finished(video)).deliver()  # type: ignore[arg-type]
    assert whole == [(OWNER, "v.ar.mp4")] and bot.sent == []
    assert say("phone_sent") in bot.said[-1][1]


def test_the_sign_in_is_kept_with_the_keys_and_dropped_when_turned_off(
        home: Path, memory_vault: Any) -> None:
    from tarjim import vault

    turn_on()
    config.save(large.SESSION, "1AbCd-session-secret")
    assert {"telegram_api_hash", large.SESSION} <= vault.SECRETS
    assert "1AbCd-session-secret" not in (home / "config.json").read_text(encoding="utf-8")
    assert not list(home.glob("*.session*"))
    large.forget()
    assert not config.setting(large.SESSION) and not large.ready()


def test_a_failure_of_the_app_protocol_never_shows_the_secrets(
        monkeypatch: pytest.MonkeyPatch) -> None:
    turn_on()

    async def explode(_work: Any) -> Any:
        raise RuntimeError(f"bad {config.setting('telegram_api_hash')}")

    monkeypatch.setattr(large, "connected", explode)
    with pytest.raises(telegram.TelegramError) as caught:
        large.send(OWNER, Path("v.mp4"))
    assert config.setting("telegram_api_hash") not in str(caught.value)
    assert not large.works()
