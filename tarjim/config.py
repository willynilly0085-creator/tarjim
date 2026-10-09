import contextlib
import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

from tarjim import vault

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
CONFIG = HOME / "config.json"
TOKEN_BYTES = 16
OWNER_DIR = 0o700
OWNER_FILE = 0o600
SAVING = threading.Lock()
TRIES = 5
PAUSE = 0.2


def settings() -> dict[str, str]:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def setting(name: str) -> str:
    from_env = os.environ.get(f"TARJIM_{name.upper()}")
    if from_env:
        return from_env
    if name in vault.SECRETS:
        return vault.read(name) or settings().get(name, "")
    return settings().get(name, "")


def private_home() -> None:
    HOME.mkdir(parents=True, exist_ok=True, mode=OWNER_DIR)
    with contextlib.suppress(OSError):
        os.chmod(HOME, OWNER_DIR)


def stored() -> dict[str, str]:
    """What a save builds on. A file that is there but busy stops the save instead of being
    replaced by an empty one; a damaged file is set aside under another name, not lost."""
    for _ in range(TRIES):
        try:
            data = json.loads(CONFIG.read_text(encoding="utf-8"))
            return {k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except ValueError:
            os.replace(CONFIG, HOME / "config.broken.json")
            return {}
        except OSError:
            time.sleep(PAUSE)
    raise PermissionError("the settings file is in use by another program")


def save(name: str, value: str) -> None:
    with SAVING:
        data = stored()
        if name in vault.SECRETS and vault.write(name, value):
            data.pop(name, None)
        else:
            data[name] = value
        write_settings(data)


def write_settings(data: dict[str, str]) -> None:
    private_home()
    handle, temporary = tempfile.mkstemp(dir=HOME, prefix=".config-")
    try:
        os.chmod(temporary, OWNER_FILE)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(json.dumps(data, ensure_ascii=False, indent=1))
        put_in_place(temporary)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def put_in_place(temporary: str) -> None:
    """On Windows the swap fails while another thread is reading the file; that passes."""
    for attempt in range(TRIES):
        try:
            os.replace(temporary, CONFIG)
            return
        except PermissionError:
            if attempt == TRIES - 1:
                raise
            time.sleep(PAUSE)


def lock_secrets() -> None:
    data = settings()
    moved = [name for name in vault.SECRETS if name in data and vault.write(name, data[name])]
    if moved:
        write_settings({k: v for k, v in data.items() if k not in moved})


def token() -> str:
    existing = setting("token")
    if existing:
        return existing
    fresh = secrets.token_hex(TOKEN_BYTES)
    save("token", fresh)
    return fresh


def prepare_environment() -> None:
    lock_secrets()
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        os.environ.setdefault(name, "1")
    models = setting("models")
    if models:
        os.environ.setdefault("HF_HOME", models)
        os.environ.setdefault("TORCH_HOME", str(Path(models) / "torch"))
    tools = Path(setting("ffmpeg")).parent if setting("ffmpeg") else None
    if tools and tools.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(tools))
        os.environ["PATH"] = f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"


def gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY") or setting("gemini_api_key")
