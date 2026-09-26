import contextlib
import json
import os
import secrets
import tempfile
from pathlib import Path

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
CONFIG = HOME / "config.json"
TOKEN_BYTES = 16
OWNER_DIR = 0o700
OWNER_FILE = 0o600


def settings() -> dict[str, str]:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def setting(name: str) -> str:
    return os.environ.get(f"TARJIM_{name.upper()}") or settings().get(name, "")


def private_home() -> None:
    HOME.mkdir(parents=True, exist_ok=True, mode=OWNER_DIR)
    with contextlib.suppress(OSError):
        os.chmod(HOME, OWNER_DIR)


def save(name: str, value: str) -> None:
    private_home()
    data = settings()
    data[name] = value
    handle, temporary = tempfile.mkstemp(dir=HOME, prefix=".config-")
    try:
        os.chmod(temporary, OWNER_FILE)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(json.dumps(data, ensure_ascii=False, indent=1))
        os.replace(temporary, CONFIG)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def token() -> str:
    existing = setting("token")
    if existing:
        return existing
    fresh = secrets.token_hex(TOKEN_BYTES)
    save("token", fresh)
    return fresh


def prepare_environment() -> None:
    models = setting("models")
    if models:
        os.environ.setdefault("HF_HOME", models)
        os.environ.setdefault("TORCH_HOME", str(Path(models) / "torch"))
        os.environ.setdefault("TTS_HOME", models)
    tools = Path(setting("ffmpeg")).parent if setting("ffmpeg") else None
    if tools and tools.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(tools))
        os.environ["PATH"] = f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"


def gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY") or setting("gemini_api_key")
