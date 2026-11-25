"""Posts X keeps from guests, and the person's own X sign-in for one download of one of them.

yt-dlp reads X as a guest. For a post X shows only to people signed in, X's answer to a guest is
a bare tombstone, {"__typename": "TweetTombstone"} with no text (2026-11-25, a post with a video;
the syndication API gave the same), and yt-dlp went on to say "No video could be found in this
tweet": the words it uses for a post with no video. tarjim reads that answer itself (watch) and
says what X did, that it hid the post from a guest. It names no reason: X gave none.

The person's own sign-in (docs/decisions.md, 2026-11-25): on their press, the browser add-on
hands over x.com's cookies for one download. They are kept in this process's memory only, never
written, logged or put in a job, and given to that one download's yt-dlp, whose cookie jar sends
a cookie only to the site it belongs to. The download takes them; an hour unused drops them.
"""
import http.cookiejar
import re
import threading
import time
import urllib.parse
from collections.abc import Callable
from typing import Any, TypeVar

SITES = ("x.com", "twitter.com")
GUEST = "X hid this post from a guest: its answer was a tombstone that gave no reason"
ACCOUNT = "X hid this post from the signed-in account too"
# yt-dlp's own words where X said why: a sensitive post, a protected account
REFUSED = ("NSFW tweet requires authentication", "this protected tweet", GUEST)
KEEP_SECONDS = 3600.0
MOST = 60
NAME = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]{1,256}")
VALUE = re.compile(r'"?[\x21\x23-\x2B\x2D-\x3A\x3C-\x5B\x5D-\x7E]{0,4096}"?')
T = TypeVar("T")
held: dict[str, tuple[float, list[http.cookiejar.Cookie]]] = {}
lock = threading.Lock()


def on_x(host: str) -> bool:
    host = host.lower().lstrip(".")
    return any(host == site or host.endswith(f".{site}") for site in SITES)


def is_x(url: str) -> bool:
    return on_x(urllib.parse.urlsplit(url.strip()).hostname or "")


def watch() -> None:
    """Puts the check in front of yt-dlp's reading of X's answer, once for each yt-dlp loaded
    (a newer one is loaded afresh, downloader.py). A yt-dlp without that step is left as it is."""
    from yt_dlp.extractor import twitter
    from yt_dlp.utils import ExtractorError

    reader = getattr(twitter.TwitterIE, "_graphql_to_legacy", None)
    if reader is None or getattr(reader, "tarjim", False):
        return

    def checked(ie: Any, data: Any, twid: Any) -> Any:
        if hidden(data):
            raise ExtractorError(ACCOUNT if ie.is_logged_in else GUEST, expected=True)
        return reader(ie, data, twid)

    checked.tarjim = True  # type: ignore[attr-defined]
    twitter.TwitterIE._graphql_to_legacy = checked


def hidden(data: Any) -> bool:
    """A tombstone with no words: one with words is X's own reason, which yt-dlp says."""
    found = data.get("tweetResult") if isinstance(data, dict) else None
    result = found.get("result") if isinstance(found, dict) else None
    return isinstance(result, dict) and result.get("__typename") == "TweetTombstone" and (
        "tombstone" not in result)


def cookie(given: Any) -> http.cookiejar.Cookie | None:
    """One cookie as the add-on read it (chrome.cookies), kept only when it belongs to X."""
    if not isinstance(given, dict):
        return None
    name, value, domain = (given.get(k) for k in ("name", "value", "domain"))
    if not (isinstance(domain, str) and on_x(domain) and isinstance(name, str)
            and isinstance(value, str) and NAME.fullmatch(name) and VALUE.fullmatch(value)):
        return None
    path = given.get("path") if isinstance(given.get("path"), str) else "/"
    return http.cookiejar.Cookie(
        0, name, value, None, False, domain, True, domain.startswith("."), path or "/", True,
        bool(given.get("secure", True)), None, True, None, None, {})


def hold(url: str, given: Any) -> int:
    """Keeps X's cookies for the next download of url; the number kept. None is kept without
    X's sign-in cookie among them: they could not sign anyone in."""
    found = [c for c in map(cookie, (given if isinstance(given, list) else [])[:MOST]) if c]
    if not is_x(url) or not any(c.name == "auth_token" for c in found):
        return 0
    with lock:
        held[url.strip()] = (time.monotonic() + KEEP_SECONDS, found)
    return len(found)


def take(url: str) -> list[http.cookiejar.Cookie]:
    """The cookies held for url, given once: they are forgotten as they are taken."""
    with lock:
        until, cookies = held.pop(url.strip(), (0.0, []))
        for old in [k for k, (end, _) in held.items() if end < time.monotonic()]:
            del held[old]
    return cookies if until >= time.monotonic() else []


def read(ydl: Any, url: str, reading: Callable[[], T]) -> T:
    """reading() with the person's sign-in when one is held for url. What X refuses while
    signed in is said as refused to the account, not to a guest."""
    watch()
    cookies = take(url)
    for one in cookies:
        ydl.cookiejar.set_cookie(one)
    try:
        return reading()
    except Exception as error:
        if cookies and any(mark in str(error) for mark in REFUSED):
            raise RuntimeError(f"{ACCOUNT} ({type(error).__name__})") from None
        raise
