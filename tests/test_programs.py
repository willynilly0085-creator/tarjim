"""A program installed after tarjim started is still found: the stale PATH is not the last word."""
from pathlib import Path

import pytest

from tarjim.engines import programs, subscription


def test_a_program_missing_from_the_old_path_is_found_on_the_current_one(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "claude.exe").write_text("", encoding="utf-8")
    (tmp_path / "claude").write_text("", encoding="utf-8")
    (tmp_path / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(programs, "current_path", lambda: str(tmp_path))
    monkeypatch.setattr(subscription, "own_folder", lambda _name: None)
    assert Path(subscription.launcher("claude")[0]).parent == tmp_path


@pytest.mark.skipif(programs.sys.platform != "win32", reason="the registry is Windows only")
def test_the_current_path_comes_from_windows_and_includes_npms_folder() -> None:
    found = programs.current_path().lower()
    assert "system32" in found and found.endswith("npm")
