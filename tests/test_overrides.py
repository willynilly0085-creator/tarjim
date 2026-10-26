"""A few libraries are installed above the exact version another package asks for, because the
newer release closes a known vulnerability and was tested with tarjim: the overrides file ships
with the release, is fetched like the tested versions, and is only ever used beside them."""
import io
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from tarjim import downloader, installer, pins, release_pins

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "https://github.com/willynilly0085-creator/tarjim/archive/refs/tags/v1.2.3.zip"
RAW = "https://raw.githubusercontent.com/willynilly0085-creator/tarjim/v1.2.3/tarjim/"
GOOD = "# tested\nrequests==2.34.2\naccelerate==1.15.0\n"


def test_every_override_is_an_exact_tested_version() -> None:
    lifted = pins.parse(pins.OVERRIDES.read_text(encoding="utf-8"))
    tested = pins.parse(pins.FILE.read_text(encoding="utf-8"))
    text = pins.OVERRIDES.read_text(encoding="utf-8")
    assert not lifted or release_pins.plain_pins(text)
    assert all(tested[name] == versions for name, versions in lifted.items())


def test_nothing_is_lifted_now_that_no_package_pins_accelerate_or_pillow() -> None:
    """qwen-asr pinned accelerate and transformers exactly and gradio held pillow back; with
    qwen-asr gone the tested versions need no override (2026-10-23)."""
    from packaging.version import Version

    assert pins.parse(pins.OVERRIDES.read_text(encoding="utf-8")) == {}
    tested = pins.parse(pins.FILE.read_text(encoding="utf-8"))
    assert "qwen-asr" not in tested and "gradio" not in tested
    (accelerate,) = tested["accelerate"]
    (transformers,) = tested["transformers"]
    assert Version(accelerate) >= Version("1.15.0") and Version(transformers) >= Version("5.13")


def test_the_pins_script_writes_what_it_lifts() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import pins as script  # type: ignore[import-not-found]
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    lifted = pins.parse(pins.OVERRIDES.read_text(encoding="utf-8"))
    assert set(lifted) == {pins.canonical(name) for name in script.LIFTED}


@pytest.mark.parametrize(("source", "address"), [
    (RELEASE, RAW + "overrides.txt"),
    ("file:///C:/plugins/tarjim", "file:///C:/plugins/tarjim/tarjim/overrides.txt"),
    ("https://github.com/someone-else/tarjim/archive/refs/tags/v1.2.3.zip", ""),
])
def test_the_overrides_come_only_from_the_same_release(source: str, address: str) -> None:
    assert release_pins.pins_address(source, release_pins.OVERRIDES) == address


def test_overrides_are_never_used_without_the_tested_versions() -> None:
    lifted = Path("overrides.txt")
    assert "--overrides" not in installer.install_command("uv", RELEASE, installer.Tested(
        None, lifted))
    command = installer.install_command("uv", RELEASE, installer.Tested(
        Path("constraints.txt"), lifted))
    assert command[command.index("--overrides") + 1] == str(lifted)
    assert command[-1] == f"tarjim[dub] @ {RELEASE}"


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(installer, "HOME", tmp_path)
    monkeypatch.setattr(installer, "LOG", tmp_path / "install.log")
    return tmp_path


def serve(monkeypatch: pytest.MonkeyPatch, files: dict[str, str]) -> list[str]:
    asked: list[str] = []

    def urlopen(address: str, timeout: float) -> io.BytesIO:
        asked.append(address)
        name = address.rsplit("/", 1)[-1]
        if name not in files:
            raise urllib.error.HTTPError(address, 404, "Not Found", {}, None)  # type: ignore[arg-type]
        return io.BytesIO(files[name].encode())

    monkeypatch.setattr(release_pins.urllib.request, "urlopen", urlopen)
    return asked


def installed_with(home: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    commands: list[list[str]] = []
    monkeypatch.setattr(installer, "run_install", lambda command: commands.append(command) or 0)
    assert installer.install("uv", RELEASE) == 0
    return commands


def test_the_install_uses_the_release_overrides(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = serve(monkeypatch, {"constraints.txt": GOOD, "overrides.txt": "accelerate==1.15.0\n"})
    (command,) = installed_with(home, monkeypatch)
    assert asked == [RAW + "constraints.txt", RAW + "overrides.txt", RAW + "python.txt"]
    assert command[command.index("--overrides") + 1] == str(home / "overrides.txt")


@pytest.mark.parametrize(("said", "python"), [
    ("3.12\n", "3.12"), (None, "3.11"), ("3.12; calc\n", "3.11"), ("--python 2.7", "3.11"),
    ("3.13", "3.13")])
def test_the_install_runs_on_the_python_the_release_names(
        home: Path, monkeypatch: pytest.MonkeyPatch, said: str | None, python: str) -> None:
    """A release names its Python in python.txt, so an update can move to a newer one; a release
    older than that file, or a file with anything but a version in it, runs on 3.11."""
    serve(monkeypatch, {"constraints.txt": GOOD, **({"python.txt": said} if said else {})})
    (command,) = installed_with(home, monkeypatch)
    assert command[command.index("--python") + 1] == python


@pytest.mark.parametrize("overrides", [None, "accelerate>=1\n", "--index-url https://x.example\n"])
def test_a_release_without_usable_overrides_installs_with_the_tested_versions_only(
        home: Path, monkeypatch: pytest.MonkeyPatch, overrides: str | None) -> None:
    files = {"constraints.txt": GOOD, **({"overrides.txt": overrides} if overrides else {})}
    serve(monkeypatch, files)
    (command,) = installed_with(home, monkeypatch)
    assert "-c" in command and "--overrides" not in command
    assert "overrides.txt" in (home / "install.log").read_text(encoding="utf-8")


def test_the_downloader_keeps_the_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    command: list[Any] = downloader.command("uv", "2026.10.5")
    assert command[command.index("-c") + 1] == str(pins.FILE)
    assert command[command.index("--overrides") + 1] == str(pins.OVERRIDES)
