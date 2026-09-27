import hmac
import re
from http.cookies import CookieError, SimpleCookie
from pathlib import Path

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


def same_origin(origin: str, host: str) -> bool:
    return origin in ("", f"http://{host}")


def extension_origin(origin: str) -> bool:
    return origin.startswith(EXTENSION_ORIGINS)
