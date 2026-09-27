import subprocess
import sys
from typing import Any

import pytest

from tarjim import quiet


@pytest.mark.skipif(sys.platform != "win32", reason="console windows exist only on Windows")
def test_helpers_start_without_a_window_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def fake_init(self: Any, *args: Any, **kwargs: Any) -> None:
        seen.append(kwargs.get("creationflags", 0))

    monkeypatch.setattr(subprocess.Popen, "__init__", fake_init)
    monkeypatch.delattr(subprocess.Popen, "_tarjim_quiet", raising=False)
    quiet.hide_child_windows()
    subprocess.Popen(["ffmpeg"])
    subprocess.Popen(["cmd"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    assert seen == [quiet.NO_WINDOW, subprocess.CREATE_NEW_CONSOLE]
    monkeypatch.delattr(subprocess.Popen, "_tarjim_quiet", raising=False)
