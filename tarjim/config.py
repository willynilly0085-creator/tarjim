import contextlib
import json
import os
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path

from tarjim import vault
from tarjim.google_ai import vertex

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
    # Beside the settings file itself: a swap across two drives is refused (EXDEV).
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=CONFIG.parent, prefix=".config-")
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
    from tarjim.model_home import fallback

    models = setting("models") or fallback(setting("models"), HOME / "models")
    if models and not setting("models"):
        save("models", models)
    if models:
        os.environ.setdefault("HF_HOME", models)
        os.environ.setdefault("TORCH_HOME", str(Path(models) / "torch"))
    tools = Path(setting("ffmpeg")).parent if setting("ffmpeg") else None
    if tools and tools.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(tools))
        os.environ["PATH"] = f"{tools}{os.pathsep}{os.environ.get('PATH', '')}"


# Gemini CLI and Google's own samples keep a key in GEMINI_API_KEY, and a Vertex AI key is often
# kept in VERTEX_API_KEY. A Vertex key goes first wherever it is found: it is billed, with no free
# daily quota, so whoever made one meant Gemini to use it (on 2026-10-27 the owner's free key, saved
# on the page, ran out on gemini-3.8-flash while a Vertex key with credit sat in VERTEX_API_KEY).
# Otherwise a key saved on tarjim's page wins over the environment's.
GEMINI = "gemini_api_key"
SPOKEN = "gemini_voice_key"  # the Gemini API key alone: Vertex AI has no voices for tarjim


def user_variable(name: str) -> str:
    """A variable set in Windows' own settings counts without restarting tarjim, which keeps the
    environment it was started with."""
    if sys.platform != "win32":
        return ""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as found:
            return str(winreg.QueryValueEx(found, name)[0])
    except OSError:
        return ""


def google_keys() -> list[str]:
    places = (setting(GEMINI), *(os.environ.get(v) or user_variable(v)
                                 for v in ("VERTEX_API_KEY", "GEMINI_API_KEY")))
    return [key for key in places if key]


def api_key(name: str) -> str:
    if name not in (GEMINI, SPOKEN):
        return setting(name)
    found = google_keys()
    studio = [key for key in found if not vertex(key)]
    if name == SPOKEN:
        return studio[0] if studio else ""
    return next((key for key in found if vertex(key)), studio[0] if studio else "")


def gemini_key() -> str:
    return api_key(GEMINI)
