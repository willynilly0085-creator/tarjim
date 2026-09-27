import json
import re
import time
from typing import Any

from tarjim.config import gemini_key

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
          "gemini-flash-latest", "gemini-3-flash-preview"]
ROUNDS = 3
RETRY_PAUSE = 3.0
MAX_WAIT = 90.0
TOO_MANY = 429
DAILY = "PerDay"
DELAY = re.compile(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s")


class QuotaExhausted(RuntimeError):
    pass


def pause_for(error: Exception) -> float:
    found = DELAY.search(str(error))
    return min(float(found.group(1)), MAX_WAIT) if found else RETRY_PAUSE


def used_up_today(error: Exception) -> bool:
    return getattr(error, "code", None) == TOO_MANY and DAILY in str(error)


class GeminiClient:
    hears = True

    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        key = api_key or gemini_key()
        if not key:
            raise RuntimeError("Gemini API key missing: set GEMINI_API_KEY or run tarjim setup")
        self.client = genai.Client(api_key=key)
        self.model_used = ""
        self.spent: set[str] = set()

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        errors: list[str] = []
        for model in MODELS * ROUNDS:
            if model in self.spent:
                continue
            try:
                return self.call(model, prompt, audio, schema)
            except Exception as error:
                errors.append(f"{model}: {getattr(error, 'code', type(error).__name__)}")
                self.note(model, error)
        if len(self.spent) == len(MODELS):
            raise QuotaExhausted("Gemini free quota is used up for today on every model")
        raise RuntimeError("all Gemini models failed: " + "; ".join(errors[-4:]))

    def note(self, model: str, error: Exception) -> None:
        if used_up_today(error):
            self.spent.add(model)
        else:
            time.sleep(pause_for(error) if getattr(error, "code", None) == TOO_MANY
                       else RETRY_PAUSE)

    def call(self, model: str, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2)
        sound = [types.Part.from_bytes(data=audio, mime_type="audio/mp3")] if audio else []
        content = types.Content(role="user", parts=[*sound, types.Part.from_text(text=prompt)])
        response = self.client.models.generate_content(
            model=model, contents=content, config=config)
        self.model_used = model
        return json.loads(response.text or "null")
