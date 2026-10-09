import os
from pathlib import Path
from typing import Any

from tarjim.engines.catalog import PROVIDERS


def service_for(home: str) -> str:
    return f"tarjim:{Path(home).resolve()}" if home else "tarjim"


SERVICE = service_for(os.environ.get("TARJIM_HOME", ""))
SECRETS = frozenset({*(p.key_name for p in PROVIDERS if p.key_name), "fish_api_key", "token",
                     "telegram_token", "eleven_api_key", "speech_api_key"})


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
