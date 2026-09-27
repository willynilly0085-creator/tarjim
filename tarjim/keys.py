import re
from collections.abc import Callable

from tarjim.config import save, setting

KEY_SHAPE = re.compile(r"^[A-Za-z0-9._-]{16,256}$")
PROVIDERS = {"gemini": "gemini_api_key", "openai": "openai_api_key",
             "anthropic": "anthropic_api_key", "fish": "fish_api_key"}


def well_formed(key: str) -> bool:
    return bool(KEY_SHAPE.match(key))


def gemini_works(key: str) -> bool:
    from google import genai

    try:
        next(iter(genai.Client(api_key=key).models.list()), None)
    except Exception:
        return False
    return True


def openai_works(key: str) -> bool:
    from tarjim.engines.openai_api import base_url
    from tarjim.engines.web import reachable

    return reachable(f"{base_url()}/models", {"Authorization": f"Bearer {key}"})


def anthropic_works(key: str) -> bool:
    from tarjim.engines.anthropic_api import VERSION
    from tarjim.engines.web import reachable

    return reachable("https://api.anthropic.com/v1/models",
                     {"x-api-key": key, "anthropic-version": VERSION})


CHECKS: dict[str, Callable[[str], bool]] = {
    "gemini": gemini_works, "openai": openai_works, "anthropic": anthropic_works}


def status() -> dict[str, bool]:
    return {provider: bool(setting(name)) for provider, name in PROVIDERS.items()}


def store(provider: str, key: str) -> str:
    key = key.strip()
    if provider not in PROVIDERS or not well_formed(key):
        return "shape"
    check = CHECKS.get(provider)
    if check and not check(key):
        return "rejected"
    save(PROVIDERS[provider], key)
    return "saved"
