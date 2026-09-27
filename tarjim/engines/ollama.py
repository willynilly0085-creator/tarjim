from typing import Any

from tarjim.config import setting
from tarjim.engines.web import parse_json, post, reachable, unwrap, wrap

BASE = "http://127.0.0.1:11434"
MODEL = "aya-expanse:8b"


def base_url() -> str:
    return (setting("ollama_url") or BASE).rstrip("/")


def available() -> bool:
    return reachable(f"{base_url()}/api/tags", {})


class OllamaAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        body = {"model": setting("local_model") or MODEL, "stream": False,
                "format": wrap(schema), "options": {"temperature": 0.2},
                "messages": [{"role": "user", "content": prompt}]}
        answer = post("local", f"{base_url()}/api/chat", {}, json=body)
        return unwrap(parse_json(answer.get("message", {}).get("content", "")))
