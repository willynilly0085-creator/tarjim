"""An engine left running while its files change keeps running the code it started with."""
import importlib
import pkgutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import tarjim
from tarjim import same_code


@pytest.fixture
def package(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "oldnew"
    (root / "inner").mkdir(parents=True)
    (root / "__init__.py").write_text("VERSION = 'old'\n", encoding="utf-8")
    (root / "inner" / "__init__.py").write_text("", encoding="utf-8")
    (root / "memory.py").write_text("def release() -> str:\n    return 'old'\n",
                                    encoding="utf-8")
    (root / "inner" / "hearing.py").write_text(
        "from oldnew.memory import release\n\ndef hear() -> str:\n    return release()\n",
        encoding="utf-8")
    yield root
    for name in [n for n in sys.modules if n.split(".")[0] == "oldnew"]:
        del sys.modules[name]


def test_a_module_changed_on_disk_after_start_is_not_used(
        package: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(package.parent))
    kept = same_code.hold(package, "oldnew")
    try:
        importlib.import_module("oldnew.memory")
        (package / "inner" / "hearing.py").write_text(
            "from oldnew.memory import heavy\n\ndef hear() -> str:\n    return heavy()\n",
            encoding="utf-8")
        (package / "__init__.py").write_text("VERSION = 'new'\n", encoding="utf-8")
        hearing = importlib.import_module("oldnew.inner.hearing")  # imported late, as a job does
        assert hearing.hear() == "old" and sys.modules["oldnew"].VERSION == "old"
        assert hearing.__file__ == str(package / "inner" / "hearing.py")
    finally:
        same_code.let_go(kept)


def test_every_module_the_engine_can_reach_is_kept() -> None:
    kept = same_code.Snapshot()
    names = {m.name for m in pkgutil.walk_packages(tarjim.__path__, "tarjim.")}
    assert names and names <= set(kept.code)
    assert "tarjim" in kept.code and "tarjim.server.__main__" in kept.code


def test_keeping_the_code_imports_nothing_heavy() -> None:
    before = set(sys.modules)
    same_code.Snapshot()
    assert set(sys.modules) == before


def test_the_fingerprint_sees_a_changed_file(package: Path) -> None:
    kept = same_code.Snapshot(package, "oldnew")
    assert not kept.changed()
    (package / "memory.py").write_text("def release() -> str:\n    return 'new!'\n",
                                       encoding="utf-8")
    assert kept.changed()


def test_the_fingerprint_sees_an_added_or_removed_file(package: Path) -> None:
    kept = same_code.Snapshot(package, "oldnew")
    (package / "voice.py").write_text("", encoding="utf-8")
    assert kept.changed()
    (package / "voice.py").unlink()
    (package / "memory.py").unlink()
    assert kept.changed()
