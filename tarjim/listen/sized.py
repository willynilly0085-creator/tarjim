"""How long a piece of sound sent to be heard is, moved out of listen/chunks.py on 2026-11-09
to make room there."""

CHUNK_SECONDS = 75.0
TAIL_SHARE = 0.3  # a last piece shorter than this share of a piece joins the one before it


def chunk_seconds() -> float:
    """The job's listen.chunk_seconds (2026-11-09). TARJIM_LISTEN_CHUNK_SECONDS still sets it
    for tests and the bench, 0 there hearing the whole clip in one request."""
    import os

    from tarjim.prefs.active import active

    raw = os.environ.get("TARJIM_LISTEN_CHUNK_SECONDS", "")
    if not raw:
        return float(active().listen.chunk_seconds)
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return CHUNK_SECONDS


def is_long(duration: float, target: float | None = None) -> bool:
    size = chunk_seconds() if target is None else target
    return size > 0 and duration > size * (1 + TAIL_SHARE)
