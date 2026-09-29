"""Fetch each provider's real model list, with the names its own app shows when it gives them.

ChatGPT (Codex) keeps its list, names, descriptions and order in ~/.codex/models_cache.json.
Gemini and Anthropic return display names from their model endpoints; OpenAI-compatible providers
return ids (OpenRouter adds names). Claude's subscription list comes from subscription_models.
"""
import json
from pathlib import Path
from typing import Any

from tarjim.config import setting
from tarjim.engines.catalog import BY_ID, SUBSCRIPTION, compatible
from tarjim.engines.model_catalog import Model, Row, describe

TIMEOUT = 10
CODEX_CACHE = Path.home() / ".codex" / "models_cache.json"


def codex_rows() -> list[Row]:
    try:
        cache = json.loads(CODEX_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    listed = [m for m in cache.get("models", []) if isinstance(m, dict) and m.get("slug")
              and m.get("visibility") != "hide"]
    listed.sort(key=lambda m: m.get("priority", 99))
    return [(str(m["slug"]), str(m.get("display_name") or ""), str(m.get("description") or ""))
            for m in listed]


def gemini_rows(key: str) -> list[Row]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT * 1000))
    return [(str(m.name).rsplit("/", maxsplit=1)[-1], str(m.display_name or ""), "")
            for m in client.models.list() if "generateContent" in (m.supported_actions or [])]


def web_rows(url: str, headers: dict[str, str]) -> list[Row]:
    import requests

    reply = requests.get(url, headers=headers, timeout=TIMEOUT)
    rows: list[Any] = reply.json().get("data", []) if reply.ok else []
    return [(str(r["id"]), str(r.get("display_name") or r.get("name") or ""), "")
            for r in rows if isinstance(r, dict) and r.get("id")]


def api_rows(provider: str) -> list[Row]:
    found = BY_ID[provider]
    key = setting(found.key_name)
    if not key:
        return []
    if provider == "gemini":
        return gemini_rows(key)
    if provider == "anthropic":
        from tarjim.engines.anthropic_api import VERSION

        return web_rows("https://api.anthropic.com/v1/models",
                        {"x-api-key": key, "anthropic-version": VERSION})
    if not compatible(found):
        return []
    from tarjim.engines.compatible import address, headers

    return web_rows(f"{address(provider)}/models", headers(key))


def models_for(provider: str) -> list[Model]:
    """The models a provider offers, shaped for the page; empty when it cannot be asked."""
    found = BY_ID.get(provider)
    if found is None:
        return []
    if provider == "claude":
        from tarjim.engines.subscription_models import claude_models

        return claude_models()
    if provider == "codex":
        return describe(codex_rows(), keep_order=True)
    if found.method == SUBSCRIPTION:
        return describe([(m, "", "") for m in found.models], keep_order=True)
    try:
        return describe(api_rows(provider))
    except Exception:
        return []
