"""Install the speaker-voice engine when the person downloads dubbing.

The package is installed without its own dependency list: that list pulls in a web interface,
speech recognition, dataset tools and cloud SDKs (41 packages) that dubbing never loads. What
dubbing does load (torch, transformers, einops, librosa, soundfile) comes with tarjim's dub extra.
"""
import importlib.util
import shutil
import subprocess
import sys

from tarjim.dub.clone import PACKAGE

MINUTES = 600


def ready() -> bool:
    return importlib.util.find_spec("voxcpm") is not None


def command() -> list[str]:
    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install", "--python", sys.executable, "--no-deps", PACKAGE]
    return [sys.executable, "-m", "pip", "install", "--no-deps", PACKAGE]


def install() -> None:
    if ready():
        return
    done = subprocess.run(command(), capture_output=True, text=True, timeout=MINUTES, check=False)
    importlib.invalidate_caches()
    if done.returncode != 0 or not ready():
        raise RuntimeError(f"could not install the voice engine: {done.stderr.strip()[-200:]}")


def repair() -> None:
    """After an update replaced the engine's folder, put the voice engine back if its model is
    still on this computer, so dubbing keeps working without asking to download again."""
    from tarjim.tools import VOICE_REPO, hub_ready

    if ready() or not hub_ready(VOICE_REPO):
        return
    try:
        install()
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        return
