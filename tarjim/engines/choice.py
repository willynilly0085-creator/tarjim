from typing import Any, Protocol

from tarjim.config import setting
from tarjim.engines.catalog import API, BY_ID, PROVIDERS, SUBSCRIPTION, compatible

LOCAL = "local"
LISTENERS = ("gemini", "openai", LOCAL)
TRANSLATORS = (*(p.id for p in PROVIDERS), LOCAL)
SUBSCRIPTIONS = tuple(p.id for p in PROVIDERS if p.method == SUBSCRIPTION)


class Asker(Protocol):
    hears: bool

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any: ...


def has_key(provider: str) -> bool:
    found = BY_ID.get(provider)
    if found is None or found.method != API or not setting(found.key_name):
        return False
    return provider != "custom" or bool(setting("custom_base_url"))


def local_translation_ready() -> bool:
    from tarjim.engines.local_servers import OLLAMA, chosen_server

    if chosen_server() != OLLAMA:
        return bool(setting("local_model"))
    from tarjim.engines.ollama import available

    return available()


def subscribed(provider: str) -> bool:
    from tarjim.engines.subscription import launcher

    return bool(launcher(BY_ID[provider].program))


def usable(provider: str, role: str) -> bool:
    if provider in SUBSCRIPTIONS:
        return role == "translate" and subscribed(provider)
    if provider == LOCAL:
        return role == "listen" or local_translation_ready()
    return has_key(provider) and (role == "translate" or provider in LISTENERS)


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


def local_translator() -> Asker:
    from tarjim.engines.local_servers import local_asker

    found = local_asker()
    if found is not None:
        return found
    from tarjim.engines.ollama import OllamaAsker

    return OllamaAsker()


def asker(provider: str) -> Asker:
    if provider in SUBSCRIPTIONS:
        from tarjim.engines.subscription import subscription_asker

        return subscription_asker(provider)  # type: ignore[no-any-return]
    if provider == LOCAL:
        return local_translator()
    if provider == "openai":
        from tarjim.engines.openai_api import OpenAIAsker

        return OpenAIAsker()
    if provider == "anthropic":
        from tarjim.engines.anthropic_api import AnthropicAsker

        return AnthropicAsker()
    if provider in BY_ID and compatible(BY_ID[provider]):
        from tarjim.engines.compatible import api_asker

        return api_asker(provider)
    from tarjim.gemini_client import GeminiClient

    return GeminiClient()
