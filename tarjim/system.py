import ctypes
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from tarjim.config import HOME, setting

GIB = 1024**3
LOCAL_VRAM = 8.0


@lru_cache(maxsize=1)
def graphics() -> dict[str, object] | None:
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    props = torch.cuda.get_device_properties(0)
    return {"name": props.name, "memory_gb": round(props.total_memory / GIB, 1)}


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
    vram = float(gpu["memory_gb"]) if gpu else 0.0  # type: ignore[arg-type]
    return {"gpu": gpu, "memory_gb": memory_gb(), "disk_free_gb": free_disk_gb(),
            "ffmpeg": bool(shutil.which("ffmpeg") or setting("ffmpeg")),
            "ollama": available(), "local_ready": vram >= LOCAL_VRAM,
            "recommended": "cloud"}
