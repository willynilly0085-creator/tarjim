from typing import Any, Protocol

from tarjim.config import setting

LISTENERS = ("gemini", "openai", "local")
TRANSLATORS = ("gemini", "openai", "anthropic", "claude", "codex", "local")
SUBSCRIPTIONS = ("claude", "codex")
KEYS = {"gemini": "gemini_api_key", "openai": "openai_api_key",
        "anthropic": "anthropic_api_key"}
LOCAL = "local"


class Asker(Protocol):
    hears: bool

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any: ...


def has_key(provider: str) -> bool:
    return bool(setting(KEYS[provider])) if provider in KEYS else False


def local_translation_ready() -> bool:
    from tarjim.engines.ollama import available

    return available()


def subscribed(provider: str) -> bool:
    from tarjim.engines.subscription import launcher

    return bool(launcher(provider))


def usable(provider: str, role: str) -> bool:
    if provider in SUBSCRIPTIONS:
        return role == "translate" and subscribed(provider)
    if provider == LOCAL:
        return role == "listen" or local_translation_ready()
    return has_key(provider)


def chosen(role: str) -> str:
    options = LISTENERS if role == "listen" else TRANSLATORS
    picked = setting(f"{role}_provider")
    if picked in options:
        return picked
    return "gemini" if has_key("gemini") else LOCAL


def chain(role: str) -> list[str]:
    first = chosen(role)
    backup = [LOCAL] if first != LOCAL and usable(LOCAL, role) else []
    return [first, *backup]


def asker(provider: str) -> Asker:
    if provider == "openai":
        from tarjim.engines.openai_api import OpenAIAsker

        return OpenAIAsker()
    if provider == "anthropic":
        from tarjim.engines.anthropic_api import AnthropicAsker

        return AnthropicAsker()
    if provider in SUBSCRIPTIONS:
        from tarjim.engines.subscription import ClaudeAsker, CodexAsker

        return ClaudeAsker() if provider == "claude" else CodexAsker()
    if provider == LOCAL:
        from tarjim.engines.ollama import OllamaAsker

        return OllamaAsker()
    from tarjim.gemini_client import GeminiClient

    return GeminiClient()
