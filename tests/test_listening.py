from typing import Any

import pytest

from tarjim.engines import app_install, listening


def test_local_listening_reports_what_is_left_to_download(monkeypatch: pytest.MonkeyPatch) -> None:
    import tarjim.system
    import tarjim.tools

    monkeypatch.setattr(tarjim.tools, "installed", lambda tool: False)
    monkeypatch.setattr(tarjim.system, "graphics", lambda: None)
    assert listening.local_status() == {"id": "local", "ready": False, "download_gb": 6.3,
                                        "gpu": False}
    monkeypatch.setattr(tarjim.tools, "installed", lambda tool: True)
    monkeypatch.setattr(tarjim.system, "graphics", lambda: {"usable": True})
    assert listening.local_status()["ready"] and listening.local_status()["gpu"]


def test_a_subscription_program_is_installed_hidden_only_when_node_is_there(
        monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[list[str]] = []

    class Process:
        def __init__(self, command: list[str], **_: Any) -> None:
            started.append(command)

        def poll(self) -> None:
            return None

    monkeypatch.setattr(app_install.subprocess, "Popen", Process)
    app_install.running.clear()
    monkeypatch.setattr(app_install, "npm", lambda: "")
    assert app_install.start("codex") == "no_node" and started == []
    assert app_install.start("claude") == "started" and started[0] == app_install.NATIVE["claude"]
    app_install.running.clear()
    monkeypatch.setattr(app_install, "npm", lambda: "npm.cmd")
    assert app_install.start("codex") == "started"
    assert started[-1] == ["npm.cmd", "install", "-g", "@openai/codex"]
    assert app_install.installing("codex")
    assert app_install.start("gemini") == "unknown"
