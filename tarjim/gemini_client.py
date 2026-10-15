import json
import re
import time
from typing import Any

from tarjim.config import gemini_key, setting

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
          "gemini-flash-latest", "gemini-3-flash-preview"]
ROUNDS = 3
RETRY_PAUSE = 3.0
MAX_WAIT = 90.0
REQUEST_MS = 240_000
# Text alone: a model that has not answered in 90 s is overloaded (seen: 160-220 s for 24 lines on
# a busy day, against 13 s on the next model), so the next one is asked instead.
TEXT_MS = 90_000
TOO_MANY = 429
REFUSED = (400, 401, 403)
DAILY = re.compile(r"per ?day", re.IGNORECASE)
DELAY = re.compile(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s")


BAD = 400


def chosen_first() -> list[str]:
    """The model the person picked is asked first; the usual list stays behind it as fallback."""
    picked = setting("gemini_model")
    return [picked, *(m for m in MODELS if m != picked)] if picked else list(MODELS)


def thinking(model: str, audio: bytes | None) -> Any:
    """Translating text needs little reasoning: Gemini 3's default long thinking only made each
    answer slower. Hearing keeps the model's default."""
    from google.genai import types

    if audio or not model.startswith("gemini-3"):
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

    def __init__(self, api_key: str | None = None) -> None:
        from google import genai
        from google.genai import types

        key = api_key or gemini_key()
        if not key:
            raise RuntimeError("Gemini API key missing: set GEMINI_API_KEY or run tarjim setup")
        # One attempt per call: the library's own silent retries waited minutes on a model Google
        # reported as overloaded (503), while the next model in the list answered in seconds.
        once = types.HttpRetryOptions(attempts=1)
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=REQUEST_MS, retry_options=once))
        self.models = chosen_first()
        self.model_used = ""
        self.spent: set[str] = set()
        self.slow: set[str] = set()  # did not answer in time: not asked again for this job
        self.cooling: dict[str, float] = {}

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        errors: list[str] = []
        for model in self.models * ROUNDS:
            if model in self.spent or model in self.slow:
                continue
            self.wait_for(model)
            try:
                return self.call(model, prompt, audio, schema)
            except Exception as error:
                errors.append(f"{model}: {getattr(error, 'code', type(error).__name__)}")
                self.note(model, error)
        if len(self.spent) == len(self.models):
            raise QuotaExhausted("Gemini free quota is used up for today on every model")
        raise RuntimeError("all Gemini models failed: " + "; ".join(errors[-4:]))

    def note(self, model: str, error: Exception) -> None:
        code = getattr(error, "code", None)
        if code == BAD and model not in MODELS:  # a chosen model that cannot do this: the rest can
            self.spent.add(model)
            return
        if code in REFUSED:
            raise RuntimeError(f"Gemini {code}: {str(error)[:160]}") from error
        if "timeout" in type(error).__name__.lower():
            self.slow.add(model)
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

    def call(self, model: str, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2,
            thinking_config=thinking(model, audio),
            http_options=None if audio else types.HttpOptions(timeout=TEXT_MS))
        sound = [types.Part.from_bytes(data=audio, mime_type="audio/mp3")] if audio else []
        content = types.Content(role="user", parts=[*sound, types.Part.from_text(text=prompt)])
        response = self.client.models.generate_content(
            model=model, contents=content, config=config)
        self.model_used = model
        if not response.text:
            raise RuntimeError("Gemini returned an empty answer")
        return json.loads(response.text)
