"""A computer that could not take the tested versions says so in the update's state."""
import pytest

from tarjim import pins, update


def test_libraries_off_their_tested_version_are_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pins, "drift", lambda: ["numpy"])
    monkeypatch.setattr(pins, "installed", lambda name: "2.1.0" if name == "numpy" else "")
    assert update.untested() == ["numpy 2.1.0"]


def test_nothing_is_listed_on_the_tested_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pins, "drift", lambda: [])
    assert update.untested() == []
