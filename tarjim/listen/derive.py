"""The code a kept transcript was derived with: the files named in listen/kept.py and every tarjim
module they import at the top of the file, and what those import, and so on.

Until 2026-11-08 only the files named were in the key, so a release that changed only
speakers.py (who a line is given to), scripts.py (how words are split for the vote and the
aligner), models.py or translate/glossary.py (which language the local words are in) kept
replaying the transcripts older code had made. An import inside a function is how this code
reaches the engines, the machine and the settings, none of which shapes what is derived from a
kept hearing, so it is not followed: following it took in most of tarjim, and every release
would have timed every clip done before it again on this computer.

Since 2026-11-08 the package itself (tarjim/__init__.py, whose version changes with every release,
reached through `from tarjim import media`) is not followed, nor the modules in NOT_FOLLOWED:
the settings, the key vault, the cloud clients, the engines and the timing check shape nothing
derived from a kept hearing, and they change often; following them timed every kept clip again
after every release.
"""
import ast
from pathlib import Path

PACKAGE = "tarjim"
NOT_FOLLOWED = frozenset({"config", "vault", "gemini_client", "google_ai", "engines",
                          "tool_catalog", "findings", "qa"})


def followed(name: str) -> bool:
    """A tarjim module below the package, outside NOT_FOLLOWED (2026-11-08)."""
    parts = name.split(".")
    return parts[0] == PACKAGE and len(parts) > 1 and parts[1] not in NOT_FOLLOWED


def top_imports(path: Path) -> set[str]:
    """The tarjim modules a file imports at its top, and the names it takes from them (a name
    may be a module of its own: `from tarjim import config`)."""
    names: set[str] = set()
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names |= {node.module, *(f"{node.module}.{alias.name}" for alias in node.names)}
        elif isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
    return {name for name in names if followed(name)}


def module_file(name: str, root: Path) -> Path | None:
    """The file of a tarjim module, under `root`, the package's folder."""
    place = root.joinpath(*name.split(".")[1:])
    return next((p for p in (place / "__init__.py", place.with_suffix(".py")) if p.is_file()),
                None)


def with_imports(files: list[Path], root: Path) -> list[Path]:
    """The files and every tarjim module they import at the top, followed to the end."""
    seen: set[Path] = set()
    todo = list(files)
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo.extend(found for name in top_imports(path) if (found := module_file(name, root)))
    return sorted(seen)
