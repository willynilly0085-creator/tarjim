from typing import Any

from tarjim.config import setting
from tarjim.engines.web import parse_json, post, unwrap, wrap
from tarjim.listen.gemini_listen import Utterance, parse

BASE = "https://api.openai.com/v1"
CHAT_MODEL = "gpt-4.1"
LISTEN_MODEL = "gpt-4o-transcribe-diarize"


def base_url() -> str:
    return (setting("openai_base_url") or BASE).rstrip("/")


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {setting('openai_api_key')}"}


class OpenAIAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        body = {"model": setting("openai_model") or CHAT_MODEL, "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_schema", "json_schema": {
                    "name": "answer", "schema": wrap(schema)}}}
        answer = post("openai", f"{base_url()}/chat/completions", headers(), json=body)
        return unwrap(parse_json(answer["choices"][0]["message"]["content"] or ""))


def listen(audio: bytes) -> tuple[str, list[Utterance]]:
    fields = {"model": setting("openai_listen_model") or LISTEN_MODEL,
              "response_format": "diarized_json", "chunking_strategy": "auto"}
    answer = post("openai", f"{base_url()}/audio/transcriptions", headers(), data=fields,
                  files={"file": ("audio.mp3", audio, "audio/mpeg")})
    rows = answer.get("segments", []) if isinstance(answer, dict) else []
    utterances = [u for row in rows if (u := parse(row)) is not None]
    return str(answer.get("language", "")), sorted(utterances, key=lambda u: u.start)
