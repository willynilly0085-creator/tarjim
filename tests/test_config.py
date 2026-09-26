import os
import stat
import sys
from pathlib import Path

import pytest

from tarjim import config


def test_saved_keys_are_readable_by_the_owner_only(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / ".tarjim"
    monkeypatch.setattr(config, "HOME", home)
    monkeypatch.setattr(config, "CONFIG", home / "config.json")
    config.save("gemini_api_key", "secret")
    config.save("token", "abc")
    assert config.settings() == {"gemini_api_key": "secret", "token": "abc"}
    assert [p.name for p in home.iterdir()] == ["config.json"]
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(home / "config.json").st_mode) == 0o600
        assert stat.S_IMODE(os.stat(home).st_mode) == 0o700
