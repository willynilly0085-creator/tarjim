from typing import Any

import pytest

from tarjim import vault


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
