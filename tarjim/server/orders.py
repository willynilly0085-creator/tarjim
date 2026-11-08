import json
from dataclasses import replace
from typing import Any

from tarjim.qualities import AUDIO, clean
from tarjim.server.jobs import Order

BLOCK = 1024 * 1024
Query = dict[str, list[str]]


def first(query: Query, key: str) -> str:
    return (query.get(key) or [""])[0].strip()


def order_from(source: str, data: dict[str, Any], name: str = "") -> Order:
    mode = str(data.get("mode") or "burn")
    quality = clean(data.get("quality"))
    sound_only = quality == AUDIO and mode != "srt"  # burning and dubbing need the picture
    tweaks = data.get("tweaks")
    return Order(source, str(data.get("target") or "ar"), mode,
                 str(data.get("dialect") or "saudi"), name, "" if sound_only else quality,
                 data.get("relisten") is True, dict(tweaks) if isinstance(tweaks, dict) else {})


def stamped(order: Order) -> Order:
    """The order with the settings it runs with, taken now, as the person sees them, with its
    own changes (2026-11-09); one already stamped keeps its own."""
    if order.prefs:
        return order
    from tarjim.prefs.job import snapshot
    from tarjim.prefs.store import current

    return replace(order, prefs=snapshot(current(order.target, order.tweaks)))


def body_size(headers: Any) -> int:
    length = str(headers.get("Content-Length", "") or "0")
    return int(length) if length.isdigit() else 0


def json_body(headers: Any, source: Any) -> dict[str, Any]:
    try:
        data = json.loads(source.read(min(body_size(headers), BLOCK)) or b"{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def copy_limited(source: Any, target: Any, size: int) -> int:
    """Copy up to size bytes and say how many arrived, so a cut-off upload can be refused."""
    left = size
    while left > 0:
        try:
            chunk = source.read(min(BLOCK, left))
        except OSError:
            break
        if not chunk:
            break
        target.write(chunk)
        left -= len(chunk)
    return size - left
