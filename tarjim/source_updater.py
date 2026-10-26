"""Bring a copy run from source (a git clone with its own environment) onto a newer release.

It used to say "updated with git" and wait for the person (the owner, 2026-10-26: "we do not want
to pull updates; we want it to update directly"). Now it updates the way an installed copy does:
the engine starts this file, copied outside its folder, and closes; this waits for it to close,
fast-forwards the clone to the release's tag (never a merge: a clone with commits of its own is
left as it is and the update is reported as failed), installs the engine and every library onto
the versions tested with that release, and starts the engine again. When the libraries cannot be
installed, the code goes back to where it was, so code and libraries still match.

Standard library only, beside its own copy of installer.py, like the installed copy's updater.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

if __package__:
    from tarjim import installer
else:  # the copy in ~/.tarjim, beside its own copy of installer.py
    import installer  # type: ignore[no-redef]

PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9.+!_-]+)\s*(;.*)?")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def git(root: Path, *args: str) -> int:
    return installer.run_install(["git", "-C", str(root), *args])


def move(root: Path, tag: str) -> bool:
    """The clone to the release's tag, only when that is a fast-forward."""
    fetched = git(root, "fetch", "--quiet", "origin", f"refs/tags/{tag}:refs/tags/{tag}") == 0
    return fetched and git(root, "merge", "--ff-only", "--quiet", tag) == 0


def pinned(constraints: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for line in constraints.read_text(encoding="utf-8").splitlines():
        match = PIN.fullmatch(line.strip())
        if match:
            found.setdefault(canonical(match[1]), set()).add(match[2])
    return found


def drift(uv: str, prefix: str, constraints: Path) -> list[str]:
    """Installed libraries at another version than the tested one (its pin picks the version)."""
    listed = subprocess.run([uv, "pip", "list", "--python", prefix, "--format", "json"],
                            capture_output=True, text=True, creationflags=installer.NO_WINDOW,
                            check=False).stdout
    tested = pinned(constraints)
    return sorted(canonical(row["name"]) for row in json.loads(listed or "[]")
                  if canonical(row["name"]) in tested
                  and row["version"] not in tested[canonical(row["name"])])


def libraries(uv: str, root: Path, prefix: str) -> int:
    """The engine itself (and whatever new it needs), then every library onto its tested version.
    The PyTorch family is not pinned, so the build for this graphics card stays."""
    constraints, overrides = root / "tarjim" / "constraints.txt", root / "tarjim" / "overrides.txt"
    tested = ["-c", str(constraints)] + (["--overrides", str(overrides)]
                                         if overrides.is_file() else [])
    base = [uv, "pip", "install", "--python", prefix, *tested]
    code = installer.run_install([*base, "-e", str(root)])
    moved = drift(uv, prefix, constraints) if code == 0 else []
    return code or (installer.run_install([*base, *moved]) if moved else 0)


def update(root: Path, tag: str, prefix: str) -> str:
    """Nothing when it is done, or why it is not."""
    uv = shutil.which("uv")
    if not uv:
        return "uv is missing: install it from https://docs.astral.sh/uv/"
    if not move(root, tag):
        return f"the clone could not move to {tag} by itself (git says why in {installer.LOG})"
    if libraries(uv, root, prefix) != 0:
        git(root, "reset", "--keep", "ORIG_HEAD")
        return f"the libraries for {tag} could not be installed, see {installer.LOG}"
    return ""


def main(chosen: argparse.Namespace) -> int:
    """chosen: the clone, the tag, the environment, the engine's start command and its process."""
    state = installer.UPDATE_STATE
    installer.wait_for_exit(chosen.after)
    installer.record("installing", f"moving the clone to {chosen.tag} and its libraries", state)
    failure = update(chosen.root, chosen.tag, chosen.prefix)
    installer.start_detached(json.loads(chosen.engine), installer.HOME / "server.log")
    installer.record("failed" if failure else "done",
                     failure or "the engine is updated and starting", state)
    return 1 if failure else 0


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("root", type=Path)
    options.add_argument("tag")
    options.add_argument("prefix")
    options.add_argument("engine", help="the engine's start command, as JSON")
    options.add_argument("--after", type=int, default=0)
    raise SystemExit(main(options.parse_args()))
