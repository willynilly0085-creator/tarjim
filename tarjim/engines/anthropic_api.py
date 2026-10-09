from typing import Any

from tarjim.config import setting
from tarjim.engines.web import EngineError, post, unwrap, wrap

URL = "https://api.anthropic.com/v1/messages"
VERSION = "2023-06-01"
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 16000
TOOL = "answer"


def headers() -> dict[str, str]:
    return {"x-api-key": setting("anthropic_api_key"), "anthropic-version": VERSION}


class AnthropicAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        from tarjim.engines.provider_models import model_in_use

        body = {"model": model_in_use("anthropic", MODEL), "max_tokens": MAX_TOKENS,
                "tools": [{"name": TOOL, "description": "Return the answer.",
                           "input_schema": wrap(schema)}],
                "tool_choice": {"type": "tool", "name": TOOL},
                "messages": [{"role": "user", "content": prompt}]}
        answer = post("anthropic", URL, headers(), json=body)
        blocks = [b for b in answer.get("content", []) if b.get("type") == "tool_use"]
        if not blocks:
            raise EngineError("anthropic", 0, f"no answer: {answer.get('stop_reason')}")
        return unwrap(blocks[0]["input"])
