"""Keep helper programs (ffmpeg, yt-dlp, claude, codex...) from flashing console windows."""
import subprocess
import sys
from typing import Any

NO_WINDOW = 0x08000000


def hide_child_windows() -> None:
    if sys.platform != "win32" or getattr(subprocess.Popen, "_tarjim_quiet", False):
        return
    original = subprocess.Popen.__init__

    def start(self: subprocess.Popen[Any], *args: Any, **kwargs: Any) -> None:
        if not kwargs.get("creationflags"):
            kwargs["creationflags"] = NO_WINDOW
        original(self, *args, **kwargs)

    subprocess.Popen.__init__ = start  # type: ignore[method-assign]
    subprocess.Popen._tarjim_quiet = True  # type: ignore[attr-defined]
