"""Posts X keeps from guests (2026-11-25): the failure says what X did, and the person's own X
sign-in is used for one download only, kept in memory, and only X's cookies are taken."""
import http.cookiejar
import time
from typing import Any

import pytest

from tarjim import x_posts
from tarjim.server.job_routes import JobRoutes
from tarjim.server.jobs import Board, Order, Task
from tarjim.server.reasons import classify

POST = "https://x.com/someone/status/2125502043737477422"
SIGNED = {"name": "auth_token", "value": "a1b2c3", "domain": ".x.com", "path": "/", "secure": True}


class DownloadError(Exception):  # yt-dlp's name, which classify reads too
    pass


@pytest.fixture(autouse=True)
def nothing_held() -> None:
    x_posts.held.clear()


def test_a_bare_tombstone_is_hidden_and_one_with_words_is_x_s_own_reason() -> None:
    assert x_posts.hidden({"tweetResult": {"result": {"__typename": "TweetTombstone"}}})
    worded = {"__typename": "TweetTombstone", "tombstone": {"text": {"text": "Deleted"}}}
    assert not x_posts.hidden({"tweetResult": {"result": worded}})
    assert not x_posts.hidden({"tweetResult": {"result": {"__typename": "Tweet"}}})
    assert not x_posts.hidden(None) and not x_posts.hidden({"tweetResult": []})


def test_yt_dlp_s_reading_of_x_is_checked_once_and_says_who_was_refused(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from yt_dlp.extractor import twitter
    from yt_dlp.utils import ExtractorError

    monkeypatch.setattr(twitter.TwitterIE, "_graphql_to_legacy", lambda ie, data, twid: "read")
    x_posts.watch()
    x_posts.watch()  # a second call never wraps it twice
    read = twitter.TwitterIE._graphql_to_legacy
    bare = {"tweetResult": {"result": {"__typename": "TweetTombstone"}}}
    guest = type("I", (), {"is_logged_in": False})()
    account = type("I", (), {"is_logged_in": True})()
    with pytest.raises(ExtractorError, match="from a guest"):
        read(guest, bare, "1")
    with pytest.raises(ExtractorError, match="signed-in account"):
        read(account, bare, "1")
    assert read(guest, {"tweetResult": {"result": {"__typename": "Tweet"}}}, "1") == "read"


def test_the_failures_are_told_apart_and_a_post_with_no_video_is_not_blamed_on_x() -> None:
    assert classify(DownloadError(f"ERROR: [twitter] 1: {x_posts.GUEST}")) == "x_signin"
    nsfw = "ERROR: [twitter] 1: NSFW tweet requires authentication. Use --cookies-from-browser"
    assert classify(DownloadError(nsfw)) == "x_signin"
    assert classify(RuntimeError(f"{x_posts.ACCOUNT} (DownloadError)")) == "x_account"
    plain = "ERROR: [twitter] 1: No video could be found in this tweet"
    assert classify(DownloadError(plain)) == "download"


def test_only_x_s_well_formed_cookies_are_held_and_never_without_its_sign_in_cookie() -> None:
    given = [SIGNED, {**SIGNED, "name": "ct0", "domain": "x.com"},
             {**SIGNED, "name": "bank", "domain": ".bank.example"},
             {**SIGNED, "name": "evil", "domain": ".notx.com"},
             {**SIGNED, "name": "crlf", "value": "a\r\nHost: other"}, "junk"]
    assert x_posts.hold(POST, given) == 2
    assert [c.name for c in x_posts.take(POST)] == ["auth_token", "ct0"]
    assert x_posts.take(POST) == []  # given once
    assert x_posts.hold(POST, [{**SIGNED, "name": "guest_id"}]) == 0
    assert x_posts.hold("https://example.com/v", [SIGNED]) == 0
    assert x_posts.hold(POST, "not a list") == 0 and not x_posts.held


def test_cookies_unused_for_an_hour_are_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    x_posts.hold(POST, [SIGNED])
    later = time.monotonic() + x_posts.KEEP_SECONDS + 1
    monkeypatch.setattr(x_posts.time, "monotonic", lambda: later)
    assert x_posts.take(POST) == []


class Reader:
    def __init__(self) -> None:
        self.cookiejar = http.cookiejar.CookieJar()


def test_the_download_gets_them_in_its_own_jar_and_a_refusal_then_names_the_account() -> None:
    x_posts.hold(POST, [SIGNED])
    ydl = Reader()
    assert x_posts.read(ydl, POST, lambda: "ok") == "ok"
    assert [c.name for c in ydl.cookiejar] == ["auth_token"]

    def refused() -> None:
        raise DownloadError("ERROR: [twitter] 1: NSFW tweet requires authentication")

    x_posts.hold(POST, [SIGNED])
    with pytest.raises(RuntimeError, match="signed-in account") as caught:
        x_posts.read(Reader(), POST, refused)
    assert "a1b2c3" not in str(caught.value)
    with pytest.raises(DownloadError):  # no sign-in held: the guest's own failure
        x_posts.read(Reader(), POST, refused)


class Routes(JobRoutes):
    def __init__(self, board: Board, body: dict[str, Any]) -> None:
        Routes.board, self.body, self.said = board, body, (0, {})

    def reply(self, code: int, payload: Any) -> None:
        self.said = (code, payload)

    def read_json(self) -> dict[str, Any]:
        return self.body


def failed(source: str, error: str) -> tuple[Board, Task]:
    def work(_task: Task) -> None:
        raise DownloadError(error)

    board = Board(work)
    task = board.submit(Order(source))
    for _ in range(100):
        if task.finished:
            break
        time.sleep(0.02)
    return board, task


def test_a_signed_in_retry_only_for_a_post_x_refused_and_the_cookies_stay_out_of_the_job() -> None:
    board, task = failed(POST, f"ERROR: [twitter] 1: {x_posts.GUEST}")
    assert task.error_code == "x_signin"
    none = Routes(board, {"cookies": [{**SIGNED, "name": "guest_id"}]})
    none.retry_signed_in({}, task.id)
    assert none.said[0] == 422 and not x_posts.held
    routes = Routes(board, {"cookies": [SIGNED]})
    routes.retry_signed_in({}, task.id)
    assert routes.said[0] == 200 and "a1b2c3" not in repr(routes.said[1])
    other, plain = failed("https://example.com/v", "ERROR: no video")
    refused = Routes(other, {"cookies": [SIGNED]})
    refused.retry_signed_in({}, plain.id)
    assert refused.said[0] == 409


EMPTY = "ERROR: [twitter] 1: Failed to parse JSON (caused by JSONDecodeError(\"Expecting value\"))"


def test_an_empty_answer_from_x_is_read_once_more_and_twice_empty_is_said_as_x_s_silence(
        monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr(x_posts.time, "sleep", slept.append)
    answers = iter([DownloadError(EMPTY), "read"])

    def reading() -> Any:
        found = next(answers)
        if isinstance(found, Exception):
            raise found
        return found

    assert x_posts.read(Reader(), POST, reading) == "read" and slept == [x_posts.PAUSE]

    def silent() -> None:
        raise DownloadError(EMPTY)

    with pytest.raises(RuntimeError, match="empty answer twice") as caught:
        x_posts.read(Reader(), POST, silent)
    assert classify(caught.value) == "x_silent"
    with pytest.raises(DownloadError):  # not X: its own failure, read once
        x_posts.read(Reader(), "https://example.com/v", silent)
    assert len(slept) == 2
