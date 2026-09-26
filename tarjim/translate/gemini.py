import json
import os
import time
from typing import Any

from tarjim.models import Cue
from tarjim.translate.clean import map_results
from tarjim.translate.prompt import build_prompt

MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
          "gemini-3.5-flash", "gemini-flash-latest"]
ROUNDS = 2
RETRY_PAUSE = 3.0
SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "ar": {"type": "string"}}, "required": ["id", "ar"]}}


class GeminiTranslator:
    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=key)
        self.model_used = ""

    def translate(self, cues: list[Cue], audio: bytes, dialect: str) -> list[Cue]:
        results = map_results(self.ask(build_prompt(cues, dialect), audio), len(cues))
        for number, cue in enumerate(cues, start=1):
            cue.text = results.get(number, "")
        return cues

    def ask(self, prompt: str, audio: bytes) -> list[dict[str, Any]]:
        errors = []
        for model in MODELS * ROUNDS:
            try:
                return self.call(model, prompt, audio)
            except Exception as error:
                errors.append(f"{model}: {type(error).__name__}")
                time.sleep(RETRY_PAUSE)
        raise RuntimeError("all Gemini models failed: " + "; ".join(errors))

    def call(self, model: str, prompt: str, audio: bytes) -> list[dict[str, Any]]:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, temperature=0.3)
        content = types.Content(role="user", parts=[
            types.Part.from_bytes(data=audio, mime_type="audio/mp3"),
            types.Part.from_text(text=prompt),
        ])
        response = self.client.models.generate_content(
            model=model, contents=content, config=config)
        self.model_used = model
        data: list[dict[str, Any]] = json.loads(response.text or "[]")
        return data
