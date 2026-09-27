import json
from typing import Any

TIMEOUT = 300
TOO_MANY = 429
OK = 200
RESULT = "result"


class EngineError(RuntimeError):
    def __init__(self, provider: str, status: int, detail: str) -> None:
        super().__init__(f"{provider} {status}: {detail[:200]}")
        self.provider = provider
        self.status = status


def wrap(schema: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": {RESULT: schema}, "required": [RESULT]}


def unwrap(value: Any) -> Any:
    return value.get(RESULT) if isinstance(value, dict) and RESULT in value else value


def parse_json(text: str) -> Any:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(cleaned or "null")


def post(provider: str, url: str, headers: dict[str, str], **payload: Any) -> Any:
    import requests

    try:
        response = requests.post(url, headers=headers, timeout=TIMEOUT, **payload)
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
