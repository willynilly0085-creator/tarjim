"""Any service that speaks the OpenAI chat format: OpenRouter, DeepSeek, Qwen, Mistral, Groq,
xAI, a custom address, or a local server such as LM Studio, Jan or llama.cpp."""
import json
from typing import Any

from tarjim.config import setting
from tarjim.engines.catalog import BY_ID
from tarjim.engines.web import parse_json, post, unwrap, wrap

LIST_TIMEOUT = 8
ANSWER_SHAPE = "Reply with one JSON object matching this schema:"


def address(provider: str) -> str:
    if provider == "custom":
        return setting("custom_base_url").rstrip("/")
    return BY_ID[provider].base_url if provider in BY_ID else ""


def headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"} if key else {}


def list_models(base_url: str, key: str = "") -> list[str]:
    import requests

    try:
        reply = requests.get(f"{base_url}/models", headers=headers(key), timeout=LIST_TIMEOUT)
        rows = reply.json().get("data", []) if reply.ok else []
    except (requests.RequestException, ValueError, AttributeError):
        return []
    return sorted(str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("id"))


class CompatibleAsker:
    hears = False

    def __init__(self, name: str, base_url: str, key: str, model: str) -> None:
        self.name, self.base_url, self.key, self.model = name, base_url, key, model

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        shape = json.dumps(wrap(schema), ensure_ascii=False)
        body = {"model": self.model, "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": f"{ANSWER_SHAPE} {shape}"},
                             {"role": "user", "content": prompt}]}
        answer = post(self.name, f"{self.base_url}/chat/completions", headers(self.key), json=body)
        return unwrap(parse_json(answer["choices"][0]["message"]["content"] or ""))


def api_asker(provider: str) -> CompatibleAsker:
    key = setting(BY_ID[provider].key_name)
    return CompatibleAsker(provider, address(provider), key, setting(BY_ID[provider].model_name))
