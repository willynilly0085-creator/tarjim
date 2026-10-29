import json
from typing import Any

TIMEOUT = 300
TOO_MANY = 429
BAD_REQUEST = 400
OK = 200
RESULT = "result"
# A computer's own model may run on the processor alone: a few words a second. It is given small
# batches, and time that grows with the prompt (about a second for every five characters).
LOCAL_CUES = 40
LOCAL_CHARS_PER_SECOND = 5


class EngineError(RuntimeError):
    def __init__(self, provider: str, status: int, detail: str) -> None:
        super().__init__(f"{provider} {status}: {detail[:200]}")
        self.provider = provider
        self.status = status


class TimedOut(EngineError):
    """A program that ran out of time: asking it again would only wait as long once more."""


def local_seconds(prompt: str) -> float:
    return float(TIMEOUT + len(prompt) // LOCAL_CHARS_PER_SECOND)


def wrap(schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": {RESULT: schema}, "required": [RESULT]}


def unwrap(value: Any) -> Any:
    return value.get(RESULT) if isinstance(value, dict) and RESULT in value else value


def parse_json(text: str) -> Any:
    """The JSON in a model's reply, also when it wrapped it in a code fence or in a sentence."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    inside = cleaned[start:end + 1] if 0 <= start < end else ""
    for candidate in (cleaned or "null", inside):
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    raise EngineError("reply", 0, f"not JSON: {cleaned[:80]}")


def reply_text(provider: str, answer: Any) -> str:
    """The words of a chat-format answer; an answer of another shape is an engine error."""
    try:
        return str(answer["choices"][0]["message"]["content"] or "")
    except (LookupError, TypeError) as error:
        raise EngineError(provider, 0, f"unexpected answer: {str(answer)[:120]}") from error


def post(provider: str, url: str, headers: dict[str, str], **payload: Any) -> Any:
    import requests

    seconds = payload.pop("timeout", TIMEOUT)
    try:
        response = requests.post(url, headers=headers, timeout=seconds, **payload)
    except requests.RequestException as error:
        raise EngineError(provider, 0, str(error)) from error
    if response.status_code != OK:
        raise EngineError(provider, response.status_code, response.text)
    return response.json()


def reachable(url: str, headers: dict[str, str]) -> bool:
    import requests

    try:
        return requests.get(url, headers=headers, timeout=15).status_code == OK
    except requests.RequestException:
        return False
