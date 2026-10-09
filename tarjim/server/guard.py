import hmac
import re
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from typing import Any

LOCAL_HOSTS = {"127.0.0.1", "localhost"}
EXTENSION_ORIGINS = ("chrome-extension://", "moz-extension://", "extension://")
MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mp3", ".m4a", ".wav",
                  ".flac", ".ogg", ".opus", ".aac"}
UNSAFE = re.compile(r"[^\w\s.\-\[\]()]", re.UNICODE)
MAX_NAME = 80
COOKIE = "tarjim"


def local_host(host: str) -> bool:
    return host.rsplit(":", 1)[0].strip("[]").lower() in LOCAL_HOSTS


def allowed_origin(origin: str) -> str:
    return origin if origin.startswith(EXTENSION_ORIGINS) else ""


def token_ok(given: str, expected: str) -> bool:
    return bool(given) and hmac.compare_digest(given.encode(), expected.encode())


def safe_name(name: str) -> str | None:
    base = Path(name.replace("\\", "/")).name
    stem, suffix = Path(base).stem, Path(base).suffix.lower()
    if suffix not in MEDIA_SUFFIXES:
        return None
    clean = UNSAFE.sub("_", stem).strip(" .")[:MAX_NAME] or "video"
    return clean + suffix


def cookie_token(header: str) -> str:
    jar = SimpleCookie()
    try:
        jar.load(header)
    except CookieError:
        return ""
    morsel = jar.get(COOKIE)
    return morsel.value if morsel else ""


def page_key(token: str) -> str:
    """What the page's cookie carries: made from the token, never the token itself, so a cookie
    seen by another program on this computer does not open the API."""
    return hmac.new(token.encode(), b"tarjim page", "sha256").hexdigest()[:32]


def from_the_page(headers: Any) -> bool:
    """A browser says where a request comes from. Another local page (a different port) is
    "same-site", never "same-origin"; a browser too old to say is judged by Origin or Referer."""
    site, own = str(headers.get("Sec-Fetch-Site", "")), f"http://{headers.get('Host', '')}"
    if site:
        return site in ("same-origin", "none")
    origin, referer = str(headers.get("Origin", "")), str(headers.get("Referer", ""))
    return origin == own or referer.startswith(f"{own}/")


def extension_origin(origin: str) -> bool:
    return origin.startswith(EXTENSION_ORIGINS)
