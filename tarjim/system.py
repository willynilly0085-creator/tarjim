import ctypes
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from tarjim.config import HOME, setting

GIB = 1024**3
LOCAL_VRAM = 8.0


CUDA_WHEELS = "https://download.pytorch.org/whl/cu128"


def nvidia_card() -> dict[str, object] | None:
    import subprocess

    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True,
                             timeout=10, check=True).stdout.strip().splitlines()
        name, memory = out[0].rsplit(",", 1)
        return {"name": name.strip(), "memory_gb": round(float(memory) / 1024, 1)}
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


@lru_cache(maxsize=1)
def graphics() -> dict[str, object] | None:
    try:
        import torch

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {"name": props.name, "memory_gb": round(props.total_memory / GIB, 1),
                    "usable": True}
    except ImportError:
        pass
    card = nvidia_card()
    return {**card, "usable": False, "fix": gpu_fix()} if card else None


def gpu_fix() -> str:
    python = Path(sys.executable).with_name("python.exe" if sys.platform == "win32" else "python")
    return (f'"{python}" -m pip install --upgrade --force-reinstall torch torchaudio '
            f"--index-url {CUDA_WHEELS}")


def memory_gb() -> float:
    if sys.platform == "win32":
        class Status(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong),
                        ("page_total", ctypes.c_ulonglong), ("page_free", ctypes.c_ulonglong),
                        ("virtual_total", ctypes.c_ulonglong),
                        ("virtual_free", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]

        status = Status()
        status.length = ctypes.sizeof(Status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return round(float(status.total) / GIB, 1)
    total = float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    return round(total / GIB, 1)


def free_disk_gb() -> float:
    place = Path(setting("models") or HOME)
    while not place.exists() and place != place.parent:
        place = place.parent
    return round(shutil.disk_usage(place).free / GIB, 1)


def describe() -> dict[str, object]:
    from tarjim.engines.ollama import available

    gpu = graphics()
    usable = bool(gpu and gpu.get("usable"))
    vram = float(gpu["memory_gb"]) if gpu and usable else 0.0  # type: ignore[arg-type]
    return {"gpu": gpu, "memory_gb": memory_gb(), "disk_free_gb": free_disk_gb(),
            "ffmpeg": bool(shutil.which("ffmpeg") or setting("ffmpeg")),
            "ollama": available(), "local_ready": vram >= LOCAL_VRAM,
            "recommended": "cloud"}
