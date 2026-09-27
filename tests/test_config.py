import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, vault


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / ".tarjim"
    monkeypatch.setattr(config, "HOME", folder)
    monkeypatch.setattr(config, "CONFIG", folder / "config.json")
    return folder


def test_keys_go_to_the_encrypted_vault_and_never_to_the_file(home: Path,
                                                              memory_vault: Any) -> None:
    config.save("gemini_api_key", "secret")
    config.save("ui_language", "ar")
    assert config.setting("gemini_api_key") == "secret"
    assert memory_vault.items[(vault.SERVICE, "gemini_api_key")] == "secret"
    on_disk = json.loads((home / "config.json").read_text(encoding="utf-8"))
    assert on_disk == {"ui_language": "ar"}
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(home / "config.json").st_mode) == 0o600


def test_keys_left_in_an_old_file_move_into_the_vault(home: Path, memory_vault: Any) -> None:
    home.mkdir()
    (home / "config.json").write_text(json.dumps({"fish_api_key": "old", "models": "D:/m"}),
                                      encoding="utf-8")
    config.lock_secrets()
    assert json.loads((home / "config.json").read_text(encoding="utf-8")) == {"models": "D:/m"}
    assert config.setting("fish_api_key") == "old"


def test_without_a_vault_keys_stay_in_the_owner_only_file(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vault, "backend", lambda: None)
    config.save("token", "abc")
    assert config.setting("token") == "abc"
    assert json.loads((home / "config.json").read_text(encoding="utf-8")) == {"token": "abc"}
