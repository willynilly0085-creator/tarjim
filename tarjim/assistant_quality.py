"""A link translated from chat starts only once the person picked its quality (the owner,
2026-10-24): translate_video without one answers with the qualities the link offers, their
sizes and the default, and the assistant asks before calling again."""
import json
from collections.abc import Callable
from typing import Any

MB = 1024 * 1024
ASK = ("Show the person these qualities with their sizes and ask which one to download; the "
       "default is 1080p or the nearest below it, and is what they get if they do not mind. Then "
       "call translate_video again with the same arguments and quality set to their pick.")
UNREAD = "The link's qualities could not be read, so it was started at 1080p or the nearest below."
A_LIST = {"started": False, "error": "list", "detail": "This link is a list of videos (a "
          "playlist, a channel, a feed): ask for the link of one video."}
UNREADABLE = 422


def refusal(found: Any) -> str:
    """The reason the engine gave for a link it cannot offer qualities for."""
    try:
        return str(json.loads(str(found.get("detail") or "{}")).get("error") or "download")
    except (ValueError, AttributeError):
        return "download"


def row(quality: str, label: str, size: int, limit: int) -> dict[str, Any]:
    return {"quality": quality, "label": label, "size_mb": round(size / MB) if size else None,
            "over_8_gb": size > limit}


def offered(found: dict[str, Any], sound: bool) -> list[dict[str, Any]]:
    limit = int(found.get("limit") or 0)
    rows = [row(c["id"], c["label"], int(c.get("size") or 0), limit) for c in found["choices"]]
    audio = found.get("audio")
    return rows + ([row("audio", "sound only", int(audio.get("size") or 0), limit)]
                   if sound and audio else [])


def to_pick(found: dict[str, Any], sound: bool) -> dict[str, Any] | None:
    """What to ask the person, or None when there is nothing to choose and the job may start."""
    if not found.get("choices"):
        return None
    return {"started": False, "title": found.get("title", ""), "default": found["default"],
            "qualities": offered(found, sound), "next": ASK}


def answer(found: Any, start: Callable[[], Any], sound: bool) -> Any:
    """found: the engine's reply about the link's qualities; start: the job without a quality."""
    if not isinstance(found, dict):
        return start()
    if found.get("error") == UNREADABLE:
        return A_LIST if refusal(found) == "list" else {**start(), "note": UNREAD}
    if "error" in found:  # tarjim is not running, or not paired with this chat
        return found
    return to_pick(found, sound) or start()
