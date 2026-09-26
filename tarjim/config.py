import json
import os
import secrets
from pathlib import Path

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
CONFIG = HOME / "config.json"
TOKEN_BYTES = 16


def settings() -> dict[str, str]:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def setting(name: str) -> str:
    return os.environ.get(f"TARJIM_{name.upper()}") or settings().get(name, "")


def save(name: str, value: str) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    data = settings()
    data[name] = value
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def token() -> str:
    existing = setting("token")
    if existing:
        return existing
    fresh = secrets.token_hex(TOKEN_BYTES)
    save("token", fresh)
    return fresh


def gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY") or setting("gemini_api_key")
