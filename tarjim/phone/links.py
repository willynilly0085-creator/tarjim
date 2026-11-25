"""Find the video link in a message, and refuse addresses that point inside the person's own
network: the bot must never be a way to make the computer fetch something private.

A name is checked by what it resolves to, so a public-looking domain that points at the home
network is refused too. Redirects are followed by the downloader; that residual risk is accepted
because only the paired account can send links (see docs/decisions.md, 2026-09-30).
"""
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlsplit

URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING = ".,;:!?)]}،؛»”’"
LOCAL_NAMES = ("localhost", ".localhost", ".local", ".internal", ".lan", ".home.arpa")


def addresses(host: str) -> list[str]:
    try:
        return [str(info[4][0]) for info in socket.getaddrinfo(host, None)]
    except (OSError, UnicodeError):
        return []


def outside(address: str) -> bool:
    try:
        return ipaddress.ip_address(address.partition("%")[0]).is_global
    except ValueError:
        return False


def public(url: str) -> bool:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
    except ValueError:
        return False
    if parts.scheme.lower() not in ("http", "https"):
        return False
    if not host or host == "localhost" or host.endswith(LOCAL_NAMES):
        return False
    found = addresses(host)
    return bool(found) and all(outside(address) for address in found)


def candidates(message: dict[str, Any]) -> list[str]:
    text = str(message.get("text") or message.get("caption") or "")
    entities = message.get("entities") or message.get("caption_entities") or []
    hidden = [str(e.get("url", "")) for e in entities if e.get("type") == "text_link"]
    return [found.rstrip(TRAILING) for found in URL.findall(text)] + hidden


def first_link(message: dict[str, Any]) -> str:
    return next((url for url in candidates(message) if public(url)), "")


def inside(url: str) -> bool:
    """Whether a link points into this computer or its network, as far as can be told: a local
    name, a private address, or a name that resolves to one. A name that does not resolve now is
    not called inside: the download then says why it failed, and a moment without DNS does not
    refuse every link."""
    try:
        host = (urlsplit(url).hostname or "").rstrip(".").lower()
    except ValueError:
        return True
    if not host or host == "localhost" or host.endswith(LOCAL_NAMES):
        return True
    return any(not outside(address) for address in addresses(host))


def linkable(url: str) -> bool:
    """A link the local server may download (server/app.py, 2026-11-25): http(s), and not inside.
    The page and the extension filtered private addresses already; a request from anywhere else
    with the token (the chat tools, steered by a stranger's text) was taken as it came."""
    return url.lower().startswith(("http://", "https://")) and not inside(url)
