"""tarjim's own Node.js comes from nodejs.org only as a release it can name exactly, in a zip whose
SHA-256 is the one Node.js published, and replaces the old folder only once it is complete."""
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tarjim.engines import node_release, own_node

V = "v24.22.1"


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(own_node, "FOLDER", tmp_path / "node")
    return tmp_path / "node"


def node_zip(version: str = V) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name in ("node.exe", "npm.cmd"):
            archive.writestr(f"node-{version}-win-x64/{name}", f"{version} {name}")
    return data.getvalue()


def sums(body: bytes, version: str = V) -> str:
    digest = hashlib.sha256(body).hexdigest()
    return (f"{'0' * 64}  node-{version}-linux-x64.tar.xz\n"
            f"{digest}  node-{version}-win-x64.zip\n{'1' * 64}  node-{version}.pkg\n")


def nodejs_org(monkeypatch: pytest.MonkeyPatch, body: bytes, listed: str) -> list[str]:
    asked: list[str] = []

    def fetch_text(url: str) -> str:
        asked.append(url)
        return listed

    def save(url: str, target: Path) -> None:
        asked.append(url)
        target.write_bytes(body)

    monkeypatch.setattr(node_release, "fetch_text", fetch_text)
    monkeypatch.setattr(node_release, "save", save)
    return asked


def npm_runs(monkeypatch: pytest.MonkeyPatch, code: int = 0) -> list[list[str]]:
    commands: list[list[str]] = []

    class Done:
        returncode, stdout, stderr = code, "", "npm error network ETIMEDOUT\n"

    def run(command: list[str], **_options: Any) -> Done:
        commands.append(command)
        return Done()

    monkeypatch.setattr(node_release.subprocess, "run", run)
    return commands


@pytest.mark.parametrize(("text", "parts"), [
    ("v24.22.1", (24, 22, 1)), ("v26.0.0", (26, 0, 0)), ("v8.17.0", (8, 17, 0)),
    ("24.22.1", ()), ("v24.22", ()), ("v24.22.1 ", ()), ("v24.22.1\n", ()), ("V24.22.1", ()),
    ("v24.22.1-rc.1", ()), ("v24.22.1; calc", ()), ("v24.22.1/../../x", ()), ("", ()),
    ("v٢٤.٢٢.١", ()), ("v" + "1" * 40 + ".0.0", ()), (24, ()), (None, ()),
])
def test_only_an_exact_release_number_is_a_version(text: Any, parts: tuple[int, ...]) -> None:
    assert node_release.number(text) == parts


def test_a_version_that_is_not_exact_never_reaches_an_address_or_a_command() -> None:
    for bad in ("v24.22.1/../../evil", "v24.22.1 & calc", "latest"):
        with pytest.raises(ValueError, match="version"):
            node_release.zip_name(bad)
    assert node_release.zip_name(V) == "node-v24.22.1-win-x64.zip"


@pytest.mark.parametrize(("found", "have", "is_newer"), [
    ("v24.22.1", "v24.18.1", True), ("v24.18.1", "v24.17.0", True), ("v26.0.0", "v24.22.1", True),
    ("v24.10.0", "v24.9.0", True), ("v24.22.1", "v24.22.1", False), ("v24.17.0", "v24.18.1", False),
    ("", "v24.17.0", False), ("v24.22.1", "", False), ("v24.22.1", "v24.17.0-pre", False),
])
def test_only_a_higher_release_counts_as_newer(found: str, have: str, is_newer: bool) -> None:
    assert node_release.newer(found, have) is is_newer


def test_the_newest_lts_with_a_windows_zip_is_taken_from_index_json() -> None:
    index = [
        {"version": "v27.1.0", "lts": False, "security": True, "files": ["win-x64-zip"]},
        {"version": "v24.23.0", "lts": "Krypton", "security": False, "files": ["linux-x64"]},
        {"version": "v24.22.1", "lts": "Krypton", "security": True, "files": ["win-x64-zip"]},
        {"version": "v22.30.0", "lts": "Jod", "security": True, "files": ["win-x64-zip"]},
    ]
    assert node_release.newest_lts(index) == "v24.22.1"


@pytest.mark.parametrize("index", [
    {}, None, "v24.22.1", [{"version": "v24.22.1; calc", "lts": "K", "files": ["win-x64-zip"]}],
    [{"version": "v24.22.1", "lts": "K", "files": "win-x64-zip"}], [7, None],
    [{"lts": "K", "files": ["win-x64-zip"]}],
])
def test_a_malformed_index_names_no_release(index: Any) -> None:
    assert node_release.newest_lts(index) == ""


def test_the_zip_must_match_its_own_line_in_shasums(tmp_path: Path) -> None:
    body = node_zip()
    target = tmp_path / "node-v24.22.1-win-x64.zip"
    target.write_bytes(body)
    node_release.verify(target, sums(body))
    target.write_bytes(body[:100] + bytes([body[100] ^ 1]) + body[101:])
    with pytest.raises(node_release.Refused, match="SHASUMS256"):
        node_release.verify(target, sums(body))
    target.write_bytes(body)
    with pytest.raises(node_release.Refused, match="does not list"):
        node_release.verify(target, sums(body).replace("win-x64.zip", "win-x86.zip"))
    with pytest.raises(node_release.Refused):
        node_release.verify(target, sums(body).upper())


def test_a_zip_that_does_not_match_is_deleted_and_nothing_is_unpacked(
        folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = node_zip()
    asked = nodejs_org(monkeypatch, body + b"tampered", sums(body))
    commands = npm_runs(monkeypatch)
    with pytest.raises(node_release.Refused):
        node_release.build(V, ["@openai/codex"])
    assert asked[0] == "https://nodejs.org/dist/v24.22.1/SHASUMS256.txt"
    assert asked[1] == "https://nodejs.org/dist/v24.22.1/node-v24.22.1-win-x64.zip"
    assert commands == [] and not folder.exists() and not own_node.staging().exists()


def test_a_checked_release_gets_the_programs_installed_before_it_takes_the_folder(
        folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (folder / "node_modules" / "@openai" / "codex").mkdir(parents=True)
    (folder / "node.exe").write_text("old", encoding="utf-8")
    body = node_zip()
    nodejs_org(monkeypatch, body, sums(body))
    commands = npm_runs(monkeypatch)
    node_release.build(V, ["@openai/codex", "@github/copilot"])
    staged = own_node.staging() / "node-v24.22.1-win-x64"
    assert commands == [[str(staged / "npm.cmd"), "install", "-g", "--prefix", str(staged),
                         "@openai/codex@latest", "@github/copilot@latest"]]
    assert (folder / "node.exe").read_text(encoding="utf-8") == "v24.22.1 node.exe"
    assert not own_node.staging().exists() and not own_node.retired().exists()


def test_a_failed_program_install_keeps_the_old_node_as_it_was(
        folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder.mkdir()
    (folder / "node.exe").write_text("old", encoding="utf-8")
    body = node_zip()
    nodejs_org(monkeypatch, body, sums(body))
    npm_runs(monkeypatch, code=1)
    with pytest.raises(node_release.Refused, match="ETIMEDOUT"):
        node_release.build(V, ["@openai/codex"])
    assert (folder / "node.exe").read_text(encoding="utf-8") == "old"
    assert not own_node.staging().exists()


def test_a_swap_that_fails_puts_the_old_folder_back(
        folder: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    folder.mkdir()
    (folder / "node.exe").write_text("old", encoding="utf-8")
    staged = tmp_path / "missing"  # renaming it fails, as a locked file would
    with pytest.raises(OSError):
        own_node.swap(staged)
    assert (folder / "node.exe").read_text(encoding="utf-8") == "old"
    folder.rename(own_node.retired())  # a crash between the two renames
    own_node.recover()
    assert (folder / "node.exe").read_text(encoding="utf-8") == "old"
    own_node.retired().mkdir()  # left behind while a program still ran from it
    own_node.recover()
    assert not own_node.retired().exists() and (folder / "node.exe").is_file()
