from typing import Any

import pytest

from tarjim import config, shortcut, vault


class MemoryVault:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, name: str) -> str | None:
        return self.items.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.items[(service, name)] = value


@pytest.fixture(autouse=True)
def memory_vault(monkeypatch: pytest.MonkeyPatch) -> Any:
    store = MemoryVault()
    monkeypatch.setattr(vault, "backend", lambda: store)
    return store


@pytest.fixture(autouse=True)
def own_desktop(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """No test writes a shortcut on the real desktop or Start menu."""
    folder = tmp_path_factory.mktemp("desktop")
    monkeypatch.setattr(shortcut, "desktop", lambda: folder / "Desktop")
    monkeypatch.setattr(shortcut, "start_menu", lambda: folder / "Programs")
    return folder


@pytest.fixture(autouse=True)
def no_outside_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test reads the Google keys kept in this computer's own environment."""
    monkeypatch.setattr(config, "user_variable", lambda _name: "")
    for name in ("VERTEX_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
