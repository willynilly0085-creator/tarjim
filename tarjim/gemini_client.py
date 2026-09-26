import json
import os
import time
from typing import Any

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
          "gemini-flash-latest", "gemini-3-flash-preview"]
ROUNDS = 3
RETRY_PAUSE = 3.0


class GeminiClient:
    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=key)
        self.model_used = ""

    def ask(self, prompt: str, audio: bytes, schema: dict[str, Any]) -> Any:
        errors = []
        for model in MODELS * ROUNDS:
            try:
                return self.call(model, prompt, audio, schema)
            except Exception as error:
                errors.append(f"{model}: {type(error).__name__}")
                time.sleep(RETRY_PAUSE)
        raise RuntimeError("all Gemini models failed: " + "; ".join(errors[-4:]))

    def call(self, model: str, prompt: str, audio: bytes, schema: dict[str, Any]) -> Any:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema, temperature=0.2)
        content = types.Content(role="user", parts=[
            types.Part.from_bytes(data=audio, mime_type="audio/mp3"),
            types.Part.from_text(text=prompt),
        ])
        response = self.client.models.generate_content(
            model=model, contents=content, config=config)
        self.model_used = model
        return json.loads(response.text or "null")
