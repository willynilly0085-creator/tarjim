"""On the phone, a link asks its quality after the kind of result: buttons with sizes, 1080p
first and ticked, sound only for a subtitle file, nothing past 8 GB, nothing remembered."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, fetch
from tarjim.phone import links
from tarjim.phone.words import say
from tests.test_phone import OWNER, FakeBot, message, pick, setup_inbox

GB = 1024 ** 3
FOUND = {"title": "talk", "default": "1080", "limit": 8 * GB, "audio": {"size": 10 * 2 ** 20},
         "choices": [{"id": "2160", "label": "2160p", "size": 9 * GB},
                     {"id": "1440", "label": "1440p", "size": int(1.5 * GB)},
                     {"id": "1080", "label": "1080p", "size": 128 * 2 ** 20},
                     {"id": "720", "label": "720p", "size": 0}]}


@pytest.fixture
def phone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(links, "addresses", lambda _host: ["142.250.1.1"])
    monkeypatch.setattr(fetch, "look", lambda _url: FOUND)
    config.save("phone_chat", str(OWNER))
    config.save("phone_target", "fr")
    return setup_inbox(tmp_path)


def shown(bot: FakeBot) -> list[tuple[str, str]]:
    return [(b["text"], b["callback_data"].split(":")[1])
            for row in bot.keyboards[-1]["inline_keyboard"] for b in row]


def test_the_qualities_follow_the_kind_of_result_with_1080p_first(phone: Any) -> None:
    inbox, bot, jobs, _pairing = phone
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    pick(inbox, bot, "go:burn:")
    assert bot.said[-1][1] == say("phone_choose_quality") and jobs.orders == []
    assert [quality for _, quality in shown(bot)] == ["1080", "1440", "720"]  # 2160p is past 8 GB
    assert shown(bot)[0][0] == "✓ " + say("qualityRow", label="1080p", size="128 MB")
    assert shown(bot)[1][0] == say("qualityRow", label="1440p", size=say("sizeGb", n="1.5"))
    assert shown(bot)[2][0] == "720p"
    pick(inbox, bot, "q:720:")
    assert [(o.mode, o.quality) for o in jobs.orders] == [("burn", "720")]


def test_sound_only_is_offered_for_a_subtitle_file_and_arabic_asks_its_style_next(
        phone: Any) -> None:
    inbox, bot, jobs, _pairing = phone
    config.save("phone_target", "ar")
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    pick(inbox, bot, "go:srt:")
    assert [quality for _, quality in shown(bot)][-1] == "audio"
    pick(inbox, bot, "q:audio:")
    assert bot.said[-1][1] == say("phone_choose_dialect") and jobs.orders == []
    pick(inbox, bot, "dl:msa:")
    assert [(o.mode, o.quality, o.dialect) for o in jobs.orders] == [("srt", "audio", "msa")]


def test_the_next_link_starts_on_1080p_again(phone: Any) -> None:
    inbox, bot, jobs, _pairing = phone
    for _ in range(2):
        inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
        pick(inbox, bot, "go:burn:")
        assert shown(bot)[0][0].startswith("✓ 1080p")
        pick(inbox, bot, "q:1440:")
    assert [o.quality for o in jobs.orders] == ["1440", "1440"]


def test_a_list_is_refused_and_an_unreadable_link_goes_on_at_1080p(
        phone: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    inbox, bot, jobs, _pairing = phone

    def refuse(_url: str) -> Any:
        raise RuntimeError(fetch.A_LIST)

    monkeypatch.setattr(fetch, "look", refuse)
    inbox.handle(bot, message(OWNER, "https://youtube.com/playlist?list=PLx"))
    pick(inbox, bot, "go:burn:")
    assert bot.said[-1][1] == say("err_list") and jobs.orders == []

    def fail(_url: str) -> Any:
        raise RuntimeError("ERROR: unable to download webpage")

    monkeypatch.setattr(fetch, "look", fail)
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    pick(inbox, bot, "go:burn:")
    assert [(o.mode, o.quality) for o in jobs.orders] == [("burn", "")]


def test_a_stale_quality_button_does_nothing(phone: Any) -> None:
    inbox, bot, jobs, _pairing = phone
    inbox.handle(bot, message(OWNER, "https://youtu.be/abc"))
    pick(inbox, bot, "go:burn:")
    pick(inbox, bot, "q:720:")
    inbox.handle(bot, {"callback_query": {"id": "q", "data": json.loads(json.dumps(
        "q:720:burn:00000000")), "message": {"chat": {"id": OWNER}, "message_id": 9}}})
    assert len(jobs.orders) == 1 and bot.said[-1][1] == say("phone_choice_expired")
