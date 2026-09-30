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
        host = (urlsplit(url).hostname or "").rstrip(".").lower()
    except ValueError:
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
