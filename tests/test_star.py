"""The request for a star on GitHub (tarjim/star.py, 2026-11-22): when it shows, what each answer
keeps, and the GitHub page when the person's own gh cannot give the star."""
import http.client
import json
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from tarjim import star
from tarjim.server import carry
from tarjim.server.app import Handler
from tarjim.server.jobs import Board, Order, Task

TOKEN = "secret-token"
DAY = 24 * 3600.0


def finish(times: int) -> None:
    for _ in range(times):
        star.counted()


def test_the_card_waits_for_enough_finished_translations() -> None:
    assert star.view() == {"ask": False, "page": star.PAGE}
    finish(star.AFTER - 1)
    assert not star.view()["ask"]
    finish(1)
    assert star.view()["ask"]


def test_later_brings_the_card_back_after_its_time_and_never_does_not() -> None:
    finish(star.AFTER)
    assert star.answer("later", now=1000.0)["answer"] == "later"
    assert not star.view(now=1000.0 + star.LATER - 1)["ask"]
    assert star.view(now=1000.0 + star.LATER)["ask"]
    assert star.answer("never")["answer"] == "never"
    assert not star.view(now=1000.0 + 365 * DAY)["ask"]


def test_the_answer_is_kept_on_disk(own_star_file: Path) -> None:
    finish(star.AFTER + 2)
    star.answer("later", now=5.0)
    assert json.loads(own_star_file.read_text(encoding="utf-8")) == {
        "done": star.AFTER + 2, "answer": "later", "until": 5.0 + star.LATER}
    own_star_file.write_text("not json", encoding="utf-8")
    assert star.read() == {"done": 0, "answer": "", "until": 0.0}


def test_a_star_given_by_gh_thanks_once_and_never_asks_again(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(star, "star_with_gh", lambda: True)
    finish(star.AFTER)
    assert star.answer("star") == {"answer": "starred", "page": star.PAGE}
    assert not star.view(now=10 ** 12)["ask"]


def test_without_gh_the_page_opens_and_the_card_does_not_come_back() -> None:
    finish(star.AFTER)
    assert star.answer("star") == {"answer": "opened", "page": star.PAGE}
    assert not star.view(now=10 ** 12)["ask"]


def test_an_unknown_answer_is_refused() -> None:
    with pytest.raises(ValueError):
        star.answer("yes")


class FakeGh:
    def __init__(self, codes: dict[str, int | Exception]) -> None:
        self.codes, self.ran = codes, []  # type: list[list[str]]

    def __call__(self, command: list[str], **_: Any) -> subprocess.CompletedProcess[bytes]:
        self.ran.append(command)
        code = self.codes[command[1]]
        if isinstance(code, Exception):
            raise code
        return subprocess.CompletedProcess(command, code)


REAL = star.star_with_gh  # taken before conftest swaps it for a test


@pytest.mark.parametrize(("codes", "starred"), [
    ({"auth": 0, "api": 0}, True),
    ({"auth": 1, "api": 0}, False),  # signed out
    ({"auth": 0, "api": 1}, False),  # GitHub refused
    ({"auth": 0, "api": subprocess.TimeoutExpired("gh", 15)}, False),
    ({"auth": OSError("gone"), "api": 0}, False),
])
def test_gh_stars_only_when_signed_in_and_any_failure_falls_back(
        monkeypatch: pytest.MonkeyPatch, codes: dict[str, int | Exception], starred: bool) -> None:
    fake = FakeGh(codes)
    monkeypatch.setattr(star.subprocess, "run", fake)
    monkeypatch.setattr(star, "gh_program", lambda: "/bin/gh")
    assert REAL() is starred
    if starred:
        assert fake.ran[-1][1:5] == ["api", "-X", "PUT", f"/user/starred/{star.REPO}"]


def test_no_gh_on_the_computer_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGh({})
    monkeypatch.setattr(star.subprocess, "run", fake)
    monkeypatch.setattr(star, "gh_program", lambda: "")
    assert REAL() is False and fake.ran == []


def test_only_a_translation_that_finished_is_counted() -> None:
    def broken(_task: Task) -> None:
        raise RuntimeError("no")

    carry.carry(Task(Order("a")), lambda _task: None, lambda _task: False)
    carry.carry(Task(Order("b")), broken, lambda _task: False)
    assert star.read()["done"] == 1


@pytest.fixture
def port(tmp_path: Path):  # type: ignore[no-untyped-def]
    Handler.board, Handler.token, Handler.uploads = Board(lambda _t: None), TOKEN, tmp_path / "up"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()


def asked(port: int, method: str, body: Any = None, token: str = TOKEN) -> tuple[int, Any]:
    link = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    link.request(method, "/star", json.dumps(body) if body is not None else None,
                 {"X-Tarjim-Token": token, "Content-Type": "application/json"})
    reply = link.getresponse()
    return reply.status, json.loads(reply.read())


def test_the_add_on_and_the_page_ask_and_answer_through_the_engine(port: int) -> None:
    finish(star.AFTER)
    assert asked(port, "GET") == (200, {"ask": True, "page": star.PAGE})
    assert asked(port, "POST", {"choice": "maybe"})[0] == 400
    assert asked(port, "POST", {"choice": "never"}) == (200, {"answer": "never", "page": star.PAGE})
    assert asked(port, "GET") == (200, {"ask": False, "page": star.PAGE})


def test_no_page_without_the_pairing_key_can_press_star(port: int) -> None:
    finish(star.AFTER)
    assert asked(port, "POST", {"choice": "star"}, token="wrong")[0] == 403
    assert star.read()["answer"] == ""


ROOT = Path(__file__).resolve().parents[1] / "tarjim"
WORDS = ("starTitle", "starText", "starYes", "starLater", "starNo", "starWorking", "starThanks",
         "starOpened")


def test_the_card_has_its_words_in_every_language_without_emoji() -> None:
    from tarjim.ui_languages import codes

    for code in codes():
        page = json.loads((ROOT / "web" / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
        add_on = json.loads((ROOT / "extension" / "_locales" / code / "messages.json")
                            .read_text(encoding="utf-8"))
        for key in WORDS:
            assert page[key] == add_on[key]["message"], (code, key)
            assert all(ord(c) < 0x1F000 for c in page[key]), (code, key)


def test_the_add_on_and_the_page_show_the_same_card() -> None:
    for folder, page in (("extension", "app.html"), ("web", "index.html")):
        html = (ROOT / folder / page).read_text(encoding="utf-8")
        assert html.index('id="star"') < html.index('class="recent"'), folder
        assert all(f'id="{name}"' in html for name in ("star-yes", "star-later", "star-no"))
    styles = [(ROOT / folder / "star.css").read_text(encoding="utf-8").splitlines()[2:]
              for folder in ("extension", "web")]
    assert styles[0] == styles[1]


def test_a_star_is_asked_for_only_from_the_persons_own_press() -> None:
    for folder in ("extension", "web"):
        code = (ROOT / folder / "star.js").read_text(encoding="utf-8")
        assert code.count('choice: "star"') == 1, folder
        assert '$("star-yes").addEventListener("click", star)' in code, folder
