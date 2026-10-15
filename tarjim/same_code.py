"""One version of tarjim's code for the whole life of an engine.

The engine imports most of its modules only when a job needs them (listening, dubbing), so an
engine left running while its files change (a `git pull` in a clone) used to load the new
version of one module beside the old version of another, and the job failed with an ImportError.
At start the engine reads every tarjim source file into memory (about 400 KB) and loads any
module imported later from that copy, never from the disk. Importing everything at start would do
the same, but the listening and dubbing modules import numpy, whose maths library commits about
30 MB per processor thread (490 MB on a 16-thread computer) even when no job ever runs.

The same pass notes each file's size and time, so the engine can tell cheaply when its code on
disk is no longer the code it runs, and restart into it when idle (server/renew.py).
"""
import importlib.abc
import importlib.util
import sys
from collections.abc import Sequence
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent
Marks = tuple[tuple[str, int, int], ...]


def files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def fingerprint(root: Path = ROOT) -> Marks:
    """Each source file's place, time and size: a few hundred stat calls, no reading."""
    marks = []
    for path in files(root):
        try:
            found = path.stat()
        except OSError:
            continue
        marks.append((path.relative_to(root).as_posix(), found.st_mtime_ns, found.st_size))
    return tuple(marks)


def module_name(path: Path, root: Path, package: str) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    return ".".join((package, *(parts[:-1] if parts[-1] == "__init__" else parts)))


class Kept(importlib.abc.SourceLoader):
    """Loads one module from the copy read at start."""

    def __init__(self, path: str, source: bytes) -> None:
        self.path, self.source = path, source

    def get_filename(self, fullname: str) -> str:
        return self.path

    def get_data(self, path: str) -> bytes:
        if path != self.path:
            raise OSError(path)  # no compiled cache: it may belong to the code on disk now
        return self.source


class Snapshot(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path = ROOT, package: str = "tarjim") -> None:
        self.root, self.marks = root, fingerprint(root)
        self.code: dict[str, tuple[Path, bytes]] = {}
        for path in files(root):
            try:
                self.code[module_name(path, root, package)] = (path, path.read_bytes())
            except OSError:
                continue

    def find_spec(self, fullname: str, path: Sequence[str] | None,
                  target: ModuleType | None = None) -> ModuleSpec | None:
        if fullname not in self.code:
            return None
        file, source = self.code[fullname]
        inside = [str(file.parent)] if file.name == "__init__.py" else None
        return importlib.util.spec_from_file_location(
            fullname, file, loader=Kept(str(file), source), submodule_search_locations=inside)

    def changed(self) -> bool:
        return fingerprint(self.root) != self.marks


KEPT: list[Snapshot] = []


def hold(root: Path = ROOT, package: str = "tarjim") -> Snapshot:
    """Called once, first thing when the engine starts."""
    snapshot = Snapshot(root, package)
    sys.meta_path.insert(0, snapshot)
    KEPT.append(snapshot)
    return snapshot


def let_go(snapshot: Snapshot) -> None:
    if snapshot in sys.meta_path:
        sys.meta_path.remove(snapshot)
    if snapshot in KEPT:
        KEPT.remove(snapshot)
