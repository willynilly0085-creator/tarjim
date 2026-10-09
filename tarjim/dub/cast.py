"""Give each speaker a voice of their own from the voices a cloud service offers, and ask a cloud
voice service for sound the same way whichever service it is."""
from typing import Any

import numpy as np

from tarjim.dub.audio import decode

OK = 200
TIMEOUT = 120
TRIES = 2
SECRET_LOOKING = 24


class VoiceError(RuntimeError):
    """A cloud voice refused or failed; the message names the service and its own reason."""


def assign(speakers: list[str], voices: list[str], first: str = "") -> dict[str, str]:
    """A different voice per speaker for as long as there are voices, then round again. The
    voice the person prefers goes to the first speaker."""
    if not voices:
        raise VoiceError("no voice to speak with: this account has no voices listed")
    order = [first, *[v for v in voices if v != first]] if first in voices else list(voices)
    return {speaker: order[at % len(order)] for at, speaker in enumerate(speakers or [""])}


def reason(reply: Any) -> str:
    """The service's own words for a refusal, short, and never with a long token in it."""
    try:
        detail = reply.json()
    except ValueError:
        detail = reply.text
    inner = detail.get("detail", detail.get("error", detail)) if isinstance(detail, dict) else ""
    words = inner.get("message", inner) if isinstance(inner, dict) else inner or detail
    return " ".join(w for w in str(words).split() if len(w) < SECRET_LOOKING)[:200]


def ask(service: str, method: str, url: str, **options: Any) -> Any:
    import requests

    for attempt in range(TRIES):
        try:
            reply = requests.request(method, url, timeout=TIMEOUT, **options)
        except requests.RequestException as error:
            if attempt == TRIES - 1:
                raise VoiceError(f"{service} 0: {type(error).__name__}") from None
            continue
        if reply.status_code == OK:
            return reply
        raise VoiceError(f"{service} {reply.status_code}: {reason(reply)}")
    raise VoiceError(f"{service} 0: no answer")


def sound(reply: Any) -> np.ndarray:
    return decode(reply.content)
