"""The voice engine is installed without its own dependencies, so tarjim has to bring everything
it imports on the way to speaking. A fresh install once lacked torchaudio and the speaker's own
voice failed on every new computer; the developer's environment had it, which hid it."""
import ast
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import pytest
from packaging.requirements import Requirement

from tarjim import pins
from tarjim.dub import voice_setup
from tarjim.dub.clone import PACKAGE

PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
# The parts of voxcpm dubbing loads; training, the command line, the web page, the denoiser and
# the text normaliser are never imported.
USED = ("__init__.py", "core.py", "model", "modules")
OPTIONAL = {"triton"}


def missing(text: str) -> list[str]:
    """What the voice engine imports that a fresh install of tarjim[dub] would not have. A
    library the release resolves comes as a dependency of another; one that floats with the
    PyTorch build is not in that list, so tarjim must name it itself."""
    project = tomllib.loads(text)["project"]
    wanted = project["dependencies"] + project["optional-dependencies"]["dub"]
    named = {pins.canonical(Requirement(line).name) for line in wanted}
    resolved = set(pins.shipped())
    return [name for name in voice_setup.LOADS if pins.canonical(name) not in named
            and (pins.floating(name) or pins.canonical(name) not in resolved)]


def test_tarjim_brings_everything_the_voice_engine_imports() -> None:
    assert missing(PROJECT.read_text(encoding="utf-8")) == []


def test_a_dub_extra_without_torchaudio_is_caught() -> None:
    text = PROJECT.read_text(encoding="utf-8").replace('"torchaudio", ', "")
    assert '"torchaudio"' not in text
    assert missing(text) == ["torchaudio"]


def imports(root: Path) -> set[str]:
    files = [file for part in USED
             for file in ([root / part] if part.endswith(".py") else (root / part).rglob("*.py"))]
    found: set[str] = set()
    for file in files:
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found - set(sys.stdlib_module_names) - {"voxcpm"}


def test_the_list_is_what_the_pinned_voice_engine_imports() -> None:
    if pins.installed("voxcpm") != PACKAGE.split("==")[1]:
        pytest.skip(f"{PACKAGE} is not installed here")
    root = Path(str(metadata.distribution("voxcpm").locate_file("voxcpm")))
    owners = metadata.packages_distributions()
    found = {pins.canonical(dist) for name in imports(root) for dist in owners.get(name, [name])}
    assert found - OPTIONAL == {pins.canonical(name) for name in voice_setup.LOADS}
