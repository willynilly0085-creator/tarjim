from collections.abc import Iterator
from typing import Any, Protocol

from tarjim.config import api_key, setting
from tarjim.engines.catalog import API, BY_ID, PROVIDERS, SUBSCRIPTION, compatible

LOCAL = "local"
LISTENERS = ("gemini", "openai", "antigravity", LOCAL)
TRANSLATORS = (*(p.id for p in PROVIDERS), LOCAL)
SUBSCRIPTIONS = tuple(p.id for p in PROVIDERS if p.method == SUBSCRIPTION)


class Asker(Protocol):
    hears: bool

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any: ...


def has_key(provider: str) -> bool:
    found = BY_ID.get(provider)
    if found is None or found.method != API or not api_key(found.key_name):
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
        return subscribed(provider) and (role == "translate" or provider in LISTENERS)
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


def soonest() -> list[str]:
    """For a short text a person waits on (text.py). Measured 2026-11-16 on four texts: an
    engine asked straight over the web with a key answered in 1.3 to 2.5 s, a subscription
    program in 4.5 to 12 s. So the engines with a key come first: the chosen one when it is one
    of them, then Gemini, then the rest, and the chosen engine behind them. A person whose
    translating engine is this computer keeps it: nothing they select is sent out."""
    usual = chosen("translate")
    if usual == LOCAL:
        return [LOCAL]
    keyed = [p.id for p in PROVIDERS if p.method == API and p.id != "custom" and has_key(p.id)]
    first = sorted(keyed, key=lambda name: (name != usual, name != "gemini"))
    return [*first, *([] if usual in first else [usual])]


def backed(first: list[str]) -> Iterator[str]:
    """These engines in turn, then this computer's AI as the backup. Whether that one runs is
    asked only once the others have failed: asking a program that is not running took two
    seconds of every selected text (measured on Windows, 2026-11-16)."""
    yield from first
    if LOCAL not in first and usable(LOCAL, "translate"):
        yield LOCAL


def tried(role: str, backup: bool) -> list[str]:
    """The chain, or the chosen engine alone when the person turned this computer's backup off
    (listen.local_backup and translate.local_backup, 2026-11-09)."""
    found = chain(role)
    return found if backup else found[:1]


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
