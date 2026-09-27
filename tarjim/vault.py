from typing import Any

SERVICE = "tarjim"
SECRETS = frozenset({"gemini_api_key", "openai_api_key", "anthropic_api_key", "fish_api_key",
                     "token"})


def backend() -> Any | None:
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return None
    return None if isinstance(keyring.get_keyring(), fail.Keyring) else keyring


def available() -> bool:
    return backend() is not None


def read(name: str) -> str:
    store = backend()
    if store is None:
        return ""
    try:
        return str(store.get_password(SERVICE, name) or "")
    except Exception:
        return ""


def write(name: str, value: str) -> bool:
    store = backend()
    if store is None:
        return False
    try:
        store.set_password(SERVICE, name, value)
    except Exception:
        return False
    return True
