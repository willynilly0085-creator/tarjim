from typing import Any

from tarjim.config import setting
from tarjim.engines.reply_check import checked, ollama_reason
from tarjim.engines.web import LOCAL_CUES, local_seconds, parse_json, post, reachable, unwrap, wrap

BASE = "http://127.0.0.1:11434"
MODEL = "aya-expanse:8b"
# Ollama keeps 4096 tokens unless told more, and silently drops the start of a longer prompt. A
# token is about two characters of Arabic or three of English; the answer is about as long as the
# prompt, so the room asked for is the prompt's length in characters, rounded up, with a margin.
SMALLEST_CONTEXT = 4096
LARGEST_CONTEXT = 32768
CONTEXT_STEP = 2048


def context_for(prompt: str) -> int:
    steps = (len(prompt) + CONTEXT_STEP) // CONTEXT_STEP + 1
    return max(SMALLEST_CONTEXT, min(LARGEST_CONTEXT, steps * CONTEXT_STEP))


def base_url() -> str:
    return (setting("ollama_url") or BASE).rstrip("/")


def available() -> bool:
    return reachable(f"{base_url()}/api/tags", {})


class OllamaAsker:
    hears = False
    most_cues = LOCAL_CUES

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        options = {"temperature": 0.2, "num_ctx": context_for(prompt)}
        body = {"model": setting("local_model") or MODEL, "stream": False,
                "format": wrap(schema), "options": options,
                "messages": [{"role": "user", "content": prompt}]}
        answer = post("local", f"{base_url()}/api/chat", {}, json=body,
                      timeout=local_seconds(prompt))
        content = checked("local", str(body["model"]), answer.get("message", {}).get("content", ""),
                          ollama_reason(answer))
        return unwrap(parse_json(content))


def installed_models() -> list[str]:
    import requests

    try:
        reply = requests.get(f"{base_url()}/api/tags", timeout=5)
        models = reply.json().get("models", []) if reply.ok else []
    except (requests.RequestException, ValueError):
        return []
    return sorted(str(m.get("name")) for m in models if m.get("name"))
