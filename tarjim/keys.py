import re
from collections.abc import Callable

from tarjim.config import api_key, save
from tarjim.engines.catalog import BY_ID, compatible
from tarjim.engines.catalog import PROVIDERS as CATALOG

KEY_SHAPE = re.compile(r"^[A-Za-z0-9._-]{16,256}$")
PROVIDERS = {**{p.id: p.key_name for p in CATALOG if p.key_name}, "fish": "fish_api_key",
             "eleven": "eleven_api_key", "speech": "speech_api_key"}

CHECK_MS = 20_000


def well_formed(key: str) -> bool:
    return bool(KEY_SHAPE.match(key))


REFUSED_BY_GOOGLE = (400, 401, 403)


def gemini_verdict(key: str) -> str:
    """"" when Google accepts the key, "rejected" when Google refuses it, "unreachable" when Google
    could not be asked (no internet, a timeout, a limit reached): that is not the key's fault, and
    calling it a bad key sent people hunting for a typo in a good one."""
    from google import genai
    from google.genai import errors, types

    # The client is kept in a name while the list is read: google-genai 2.33 closes a client the
    # moment nothing holds it, so the inline form failed every key ("client has been closed").
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=CHECK_MS))
    try:
        next(iter(client.models.list()), None)
    except errors.APIError as error:
        return "rejected" if error.code in REFUSED_BY_GOOGLE else "unreachable"
    except Exception:
        return "unreachable"
    return ""


def openai_works(key: str) -> bool:
    from tarjim.engines.openai_api import base_url
    from tarjim.engines.web import reachable

    return reachable(f"{base_url()}/models", {"Authorization": f"Bearer {key}"})


def anthropic_works(key: str) -> bool:
    from tarjim.engines.anthropic_api import VERSION
    from tarjim.engines.web import reachable

    return reachable("https://api.anthropic.com/v1/models",
                     {"x-api-key": key, "anthropic-version": VERSION})


def eleven_works(key: str) -> bool:
    from tarjim.dub.eleven import works

    return works(key)


CHECKS: dict[str, Callable[[str], bool]] = {
    "openai": openai_works, "anthropic": anthropic_works,
    "eleven": eleven_works}


def compatible_works(provider: str, key: str) -> bool:
    from tarjim.engines.compatible import address, list_models

    return bool(address(provider)) and bool(list_models(address(provider), key))


def status() -> dict[str, bool]:
    return {provider: bool(api_key(name)) for provider, name in PROVIDERS.items()}


def verdict(provider: str, key: str) -> str:
    if provider == "gemini":
        return gemini_verdict(key)
    check = CHECKS.get(provider)
    fits = compatible(BY_ID[provider]) if provider in BY_ID else False
    if (check and not check(key)) or (not check and fits and not compatible_works(provider, key)):
        return "rejected"
    return ""


def store(provider: str, key: str) -> str:
    key = key.strip()
    if provider not in PROVIDERS or not well_formed(key):
        return "shape"
    refused = verdict(provider, key)
    if refused:
        return refused
    save(PROVIDERS[provider], key)
    return "saved"
