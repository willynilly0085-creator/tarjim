"""Every library but yt-dlp and the PyTorch family is installed at the version tested with the
release, and an install that came from an older installer is brought onto them once."""
import io
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, installer, pins, release_pins, update
from tarjim.server import update_routes

RELEASE = "https://github.com/willynilly0085-creator/tarjim/archive/refs/tags/v1.2.3.zip"
RAW = "https://raw.githubusercontent.com/willynilly0085-creator/tarjim/v1.2.3/tarjim/constraints.txt"
GOOD = "# tested\nnumpy==2.4.6 ; python_full_version < '3.12'\nnumpy==2.5.4 ; python_full_version" \
       " >= '3.12'\nrequests==2.34.2\n"


def test_the_shipped_file_pins_everything_except_what_moves_by_itself() -> None:
    text = pins.FILE.read_text(encoding="utf-8")
    found = pins.parse(text)
    assert {"numpy", "transformers", "requests", "mcp", "demucs"} <= set(found)
    assert not [name for name in found if pins.floating(name)]
    assert {"yt-dlp", "torch", "torchaudio", "torchcodec"}.isdisjoint(found)
    lines = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert all(release_pins.PIN.fullmatch(line) for line in lines)


@pytest.mark.parametrize(("name", "moves"), [
    ("yt-dlp", True), ("yt_dlp", True), ("torch", True), ("TorchAudio", True), ("torchcodec", True),
    ("nvidia-cublas", True), ("cuda-bindings", True), ("triton", True), ("sympy", True),
    ("numpy", False), ("transformers", False), ("demucs", False), ("torchmetrics", False),
])
def test_what_moves_by_itself_is_known(name: str, moves: bool) -> None:
    assert pins.floating(name) is moves


def test_drift_lists_installed_libraries_at_another_version(
        monkeypatch: pytest.MonkeyPatch) -> None:
    have = {"numpy": "2.4.6", "requests": "2.31.0"}
    monkeypatch.setattr(pins, "installed", lambda name: have.get(name, ""))
    assert pins.drift(pins.parse(GOOD)) == ["requests"]
    have["requests"] = "2.34.2"
    assert pins.drift(pins.parse(GOOD)) == []


def test_the_install_carries_upgrade_and_the_tested_versions(tmp_path: Path) -> None:
    file = tmp_path / "constraints.txt"
    command = installer.install_command("uv", RELEASE, file)
    assert command[-1] == f"tarjim[dub] @ {RELEASE}" and "--upgrade" in command
    assert command[command.index("-c") + 1] == str(file)
    assert "--torch-backend" in command and "--upgrade" not in installer.install_command(
        "uv", RELEASE, None) and "-c" not in installer.install_command("uv", RELEASE, None)


@pytest.mark.parametrize(("source", "address"), [
    (RELEASE, RAW),
    ("https://github.com/someone-else/tarjim/archive/refs/tags/v1.2.3.zip", ""),
    ("https://github.com/willynilly0085-creator/tarjim/archive/refs/tags/v1.2.3.zip?x=1", ""),
    ("https://github.com/willynilly0085-creator/tarjim/archive/refs/heads/master.zip", ""),
    ("http://github.com/willynilly0085-creator/tarjim/archive/refs/tags/v1.2.3.zip", ""),
    ("file:///C:/plugins/tarjim", "file:///C:/plugins/tarjim/tarjim/constraints.txt"),
])
def test_the_tested_versions_come_only_from_the_same_release(source: str, address: str) -> None:
    assert release_pins.pins_address(source) == address


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for module, name in ((installer, "HOME"), (config, "HOME")):
        monkeypatch.setattr(module, name, tmp_path)
    monkeypatch.setattr(installer, "LOG", tmp_path / "install.log")
    monkeypatch.setattr(installer, "STATE", tmp_path / "install.json")
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    return tmp_path


def serve(monkeypatch: pytest.MonkeyPatch, body: str | Exception) -> list[str]:
    asked: list[str] = []

    def urlopen(address: str, timeout: float) -> io.BytesIO:
        asked.append(address)
        if isinstance(body, Exception):
            raise body
        return io.BytesIO(body.encode())

    monkeypatch.setattr(release_pins.urllib.request, "urlopen", urlopen)
    return asked


@pytest.mark.parametrize("body", [urllib.error.URLError("offline"), "numpy==1\n--index-url https:"
                                  "//elsewhere.example/simple\n", "", "\xff not text"])
def test_without_the_tested_versions_the_install_still_happens_as_before(
        home: Path, monkeypatch: pytest.MonkeyPatch, body: str | Exception) -> None:
    serve(monkeypatch, body)
    assert release_pins.tested_versions(RELEASE, home) is None
    assert "installing without it" in (home / "install.log").read_text(encoding="utf-8")


def test_the_tested_versions_are_saved_for_uv(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = serve(monkeypatch, GOOD)
    saved = release_pins.tested_versions(RELEASE, home)
    assert asked == [RAW] and saved is not None and saved.read_text(encoding="utf-8") == GOOD


def installs(home: Path, monkeypatch: pytest.MonkeyPatch, codes: list[int]) -> list[list[str]]:
    commands: list[list[str]] = []

    class Done:
        def __init__(self, code: int) -> None:
            self.returncode = code

    def run(command: list[str], **_options: Any) -> Done:
        commands.append(command)
        return Done(codes[len(commands) - 1])

    monkeypatch.setattr(installer.shutil, "which", lambda _name: "uv")
    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(installer, "server_program", lambda _uv: "tarjim-serve")
    monkeypatch.setattr(installer, "start_detached", lambda _command, _log: None)
    return commands


def test_a_failed_download_of_the_tested_versions_falls_back(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, urllib.error.URLError("offline"))
    commands = installs(home, monkeypatch, [0])
    assert installer.main(RELEASE) == 0
    assert commands == [installer.install_command("uv", RELEASE, None)]


def test_an_install_the_tested_versions_cannot_satisfy_is_tried_again_as_before(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, GOOD)
    commands = installs(home, monkeypatch, [1, 0])
    assert installer.main(RELEASE) == 0
    assert "-c" in commands[0] and commands[1] == installer.install_command("uv", RELEASE, None)


@pytest.fixture
def engine(home: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    started: list[str] = []
    monkeypatch.setattr(update, "__version__", "1.2.3")
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(update, "latest", lambda: "v1.2.3")
    monkeypatch.setattr(pins, "drift", lambda: ["requests"])
    monkeypatch.setattr(update, "start", lambda tag, _port: started.append(tag) or True)
    monkeypatch.setattr(update_routes.threading, "Timer", lambda *_args: type(
        "Timer", (), {"start": lambda self: None})())
    monkeypatch.setattr(update_routes.downloader, "refresh", lambda idle: "")
    # nothing outside this test's home: not the real ~/.tarjim/node, ffmpeg or uv
    monkeypatch.setattr(update_routes.node_update, "refresh", lambda idle: "")
    monkeypatch.setattr(update_routes.ffmpeg_update, "refresh", lambda idle: "")
    monkeypatch.setattr(update_routes.python_update, "refresh", lambda idle, port: False)
    return started


class Idle:
    def recent(self) -> list[Any]:
        return []


def test_an_install_off_the_tested_versions_is_repaired_once(engine: list[str]) -> None:
    update_routes.look(Idle(), 17653)  # type: ignore[arg-type]
    update_routes.look(Idle(), 17653)  # type: ignore[arg-type]
    assert engine == ["v1.2.3"] and config.setting("repaired_for") == "1.2.3"


@pytest.mark.parametrize("why", ["matches", "cannot install", "automatic off", "newer release"])
def test_no_repair_when_not_needed_or_not_allowed(
        engine: list[str], monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    if why == "matches":
        monkeypatch.setattr(pins, "drift", lambda: [])
    if why == "cannot install":
        monkeypatch.setattr(update, "can_install", lambda: False)
    if why == "automatic off":
        config.save("auto_update", "no")
    if why == "newer release":
        monkeypatch.setattr(update, "latest", lambda: "v1.2.4")
    update_routes.look(Idle(), 17653)  # type: ignore[arg-type]
    assert engine == (["v1.2.4"] if why == "newer release" else [])
