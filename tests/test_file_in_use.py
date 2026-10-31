"""A result whose earlier copy another program holds open is moved once it is let go, and a copy
held for good is reported in the person's words, not as an unexpected error."""
from pathlib import Path

import pytest

from tarjim import whole
from tarjim.server.reasons import classify


def test_the_move_waits_for_a_program_to_let_go(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part, target = tmp_path / "a.part.mp4", tmp_path / "a.mp4"
    part.write_bytes(b"new")
    target.write_bytes(b"old")
    real, refusals = whole.os.replace, [PermissionError("held")] * 3
    monkeypatch.setattr(whole.time, "sleep", lambda _s: None)

    def replace(a: Path, b: Path) -> None:
        if refusals:
            raise refusals.pop()
        real(a, b)

    monkeypatch.setattr(whole.os, "replace", replace)
    whole.move(part, target)
    assert target.read_bytes() == b"new" and not part.exists()


def test_a_file_held_for_good_is_reported_as_open_elsewhere(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(whole.time, "sleep", lambda _s: None)
    monkeypatch.setattr(whole.os, "replace", lambda _a, _b: (_ for _ in ()).throw(
        PermissionError("[WinError 5] Access is denied")))
    with pytest.raises(PermissionError) as caught:
        whole.move(tmp_path / "a.part.mp4", tmp_path / "clip download.ar.mp4", patience=1.0)
    assert classify(caught.value) == "in_use"
