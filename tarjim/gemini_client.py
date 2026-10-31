import json
import re
import time
from collections.abc import Iterator
from typing import Any

from tarjim.config import gemini_key, setting
from tarjim.google_ai import google_client

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
          "gemini-flash-latest", "gemini-3-flash-preview"]
ROUNDS = 3
RETRY_PAUSE = 3.0
MAX_WAIT = 90.0
# Listening to a long recording may take minutes, so it gets 4 of them.
REQUEST_MS = 240_000
# Everything else, translation included: a model that has not answered in 90 s is overloaded
# (seen: 160-220 s for 24 lines on a busy day, against 13 s on the next model), so the next one is
# asked instead. Google holds a request until this limit. Translation carries the clip's sound
# (48 kb/s mp3) and gets half a second more per second of it: 5 minutes took 78 s on a busy day.
ANSWER_MS = 90_000
SOUND_BYTES_PER_SECOND = 6_000
MS_PER_SOUND_SECOND = 500
# A model that kept a job waiting this long and still failed is asked again in that job only when
# no other is left, and goes last for the next jobs for a while (seen: 240 s and 136 s lost on two
# models before the third translated a 63 s clip in 25 s).
LONG_WAIT = 30.0
STALLED_FOR = 20 * 60.0
STALLED: dict[str, float] = {}
TOO_MANY = 429
USED_UP = "daily quota used up"
# A 400 or 403 is about one model (not offered to this key, or not able to do this request): the
# next one is asked. A 401, or one that names the key ("API key not valid" comes as a 400), is the
# key itself, which no other model will accept either.
REFUSED = (400, 403)
BAD_KEY = 401
KEY = re.compile(r"api[ _]?key", re.IGNORECASE)
DAILY = re.compile(r"per ?day", re.IGNORECASE)
DELAY = re.compile(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s")


def chosen_first() -> list[str]:
    """The model the person picked is asked first; the usual list stays behind it as fallback."""
    picked = setting("gemini_model")
    return [picked, *(m for m in MODELS if m != picked)] if picked else list(MODELS)


def asked_last_if_stalled(models: list[str]) -> list[str]:
    now = time.monotonic()
    return sorted(models, key=lambda model: STALLED.get(model, 0.0) > now)


def thinking(model: str, listening: bool) -> Any:
    """Translating needs little reasoning, even with the clip's sound beside the text: Gemini 3's
    default long thinking only made each answer slower. Listening keeps the model's default."""
    from google.genai import types

    if listening or not model.startswith("gemini-3"):
        return None
    return types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)


class QuotaExhausted(RuntimeError):
    pass


def pause_for(error: Exception) -> float:
    found = DELAY.search(str(error))
    return min(float(found.group(1)), MAX_WAIT) if found else RETRY_PAUSE


def used_up_today(error: Exception) -> bool:
    return getattr(error, "code", None) == TOO_MANY and bool(DAILY.search(str(error)))


class GeminiClient:
    hears = True

    def __init__(self, api_key: str | None = None, listening: bool = False) -> None:
        from google.genai import types

        key = api_key or gemini_key()
        if not key:
            raise RuntimeError("Gemini API key missing: set GEMINI_API_KEY or run tarjim setup")
        # One attempt per call: the library's own silent retries waited minutes on a model Google
        # reported as overloaded (503), while the next model in the list answered in seconds.
        once = types.HttpRetryOptions(attempts=1)
        self.client = google_client(key, types.HttpOptions(timeout=REQUEST_MS, retry_options=once))
        self.listening = listening
        self.models = asked_last_if_stalled(chosen_first())
        self.model_used = ""
        self.spent: set[str] = set()  # daily quota used up
        self.refused: set[str] = set()  # this model will not take the request
        self.slow: set[str] = set()  # did not answer in time: not asked again for this job
        self.cooling: dict[str, float] = {}

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        failed: dict[str, str] = {}  # each model's last reason, so the error names every one
        for model in self.turns():
            self.wait_for(model)
            started = time.monotonic()
            try:
                return self.call(model, prompt, audio, schema)
            except Exception as error:
                failed[model] = USED_UP if used_up_today(error) else str(
                    getattr(error, "code", type(error).__name__))
                self.note(model, error, time.monotonic() - started)
        raise self.gave_up(failed)

    def gave_up(self, failed: dict[str, str]) -> RuntimeError:
        """Seen 2026-10-27: a free key had used up its day on gemini-3.8 to 3.5, and the error
        named only the last model left, busy four times over, as if tarjim had picked it."""
        if len(self.spent) == len(self.models):
            return QuotaExhausted("Gemini free quota is used up for today on every model")
        reasons = "; ".join(f"{model}: {why}" for model, why in failed.items())
        codes = set(failed.values())
        if codes and codes <= {str(code) for code in REFUSED}:  # " 403:" names a key problem
            return RuntimeError(f"Gemini {max(codes)}: every model refused: {reasons}")
        if USED_UP in failed.values():  # still a RuntimeError: listening falls back to local
            return RuntimeError(f"Gemini free daily quota is used up, the rest are busy: {reasons}")
        return RuntimeError(f"all Gemini models failed: {reasons}")

    def turns(self) -> Iterator[str]:
        """Three rounds over the models that answer; the ones that kept us waiting only when every
        other has failed."""
        for model in self.models * ROUNDS:
            if model not in self.spent | self.slow | self.refused:
                yield model
        yield from (model for model in self.models if model not in self.spent | self.refused)

    def note(self, model: str, error: Exception, waited: float = 0.0) -> None:
        code = getattr(error, "code", None)
        if code == BAD_KEY or (code in REFUSED and KEY.search(str(error))):
            raise RuntimeError(f"Gemini {code}: {str(error)[:160]}") from error
        if code in REFUSED:  # not counted as a used-up quota: the next model is asked
            self.refused.add(model)
            return
        if waited >= LONG_WAIT or "timeout" in type(error).__name__.lower():
            self.slow.add(model)
            STALLED[model] = time.monotonic() + STALLED_FOR
            return
        if used_up_today(error):
            self.spent.add(model)
            return
        busy = getattr(error, "code", None) == TOO_MANY
        self.cooling[model] = time.monotonic() + (pause_for(error) if busy else RETRY_PAUSE)

    def wait_for(self, model: str) -> None:
        remaining = self.cooling.get(model, 0.0) - time.monotonic()
        if remaining > 0:
            time.sleep(min(remaining, MAX_WAIT))

    def limit_ms(self, audio: bytes | None) -> int:
        if self.listening:
            return REQUEST_MS
        seconds = len(audio or b"") / SOUND_BYTES_PER_SECOND
        return min(REQUEST_MS, ANSWER_MS + int(seconds * MS_PER_SOUND_SECOND))

    def call(self, model: str, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2,
            thinking_config=thinking(model, self.listening),
            http_options=types.HttpOptions(timeout=self.limit_ms(audio)))
        sound = [types.Part.from_bytes(data=audio, mime_type="audio/mp3")] if audio else []
        content = types.Content(role="user", parts=[*sound, types.Part.from_text(text=prompt)])
        response = self.client.models.generate_content(
            model=model, contents=content, config=config)
        self.model_used = model
        from tarjim.engines.reply_check import checked, gemini_reason

        return json.loads(checked("gemini", model, response.text, gemini_reason(response)))
