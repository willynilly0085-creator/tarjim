"""Firefox keeps for good only an add-on Mozilla has signed: on 2026-11-15 the owner was adding
the temporary one again on every start. The signed one is not in Mozilla's shop, so it says
itself where it learns of a newer version, and the two keys that sign it never reach a command
line."""
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import tarjim
from tarjim import extension_home

ROOT = Path(tarjim.__file__).resolve().parents[1]


@pytest.fixture
def signing() -> Any:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import firefox_addon
        yield firefox_addon
    finally:
        sys.path.remove(str(ROOT / "scripts"))


def test_the_firefox_add_on_says_where_its_updates_are() -> None:
    gecko = json.loads(extension_home.firefox_manifest())["browser_specific_settings"]["gecko"]
    assert gecko["update_url"] == extension_home.UPDATES
    assert extension_home.UPDATES.startswith("https://raw.githubusercontent.com/")
    assert extension_home.UPDATES.endswith("/master/firefox-updates.json")


def test_the_updates_file_offers_this_version_from_its_own_release() -> None:
    told = json.loads((ROOT / "firefox-updates.json").read_text(encoding="utf-8"))
    assert told == extension_home.updates(tarjim.__version__)
    [offer] = told["addons"][extension_home.GECKO_ID]["updates"]
    assert offer["version"] == tarjim.__version__
    assert offer["update_link"].startswith("https://github.com/")
    assert offer["update_link"].endswith(
        f"/releases/download/v{tarjim.__version__}/tarjim-firefox.xpi")


def test_what_is_signed_is_the_packaged_add_on_with_firefoxs_manifest(
        signing: ModuleType, tmp_path: Path) -> None:
    made = signing.folder(tmp_path)
    assert (made / "manifest.json").read_text(encoding="utf-8") == (
        extension_home.firefox_manifest())
    assert (made / "jobs.js").read_bytes() == (extension_home.PACKAGED / "jobs.js").read_bytes()


def test_the_keys_reach_the_signer_in_its_environment_and_nowhere_else(
        signing: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    ran: list[tuple[list[str], dict[str, str]]] = []

    def signer(command: list[str], **how: Any) -> None:
        ran.append((command, how["env"]))
        (tmp_path / "out" / "anything-1.0.xpi").write_bytes(b"signed")

    monkeypatch.setenv("AMO_JWT_ISSUER", "user:1:2")
    monkeypatch.setenv("AMO_JWT_SECRET", "not-a-real-secret")
    monkeypatch.setattr(subprocess, "run", signer)
    (tmp_path / "out").mkdir()
    signed = signing.sign(tmp_path / "addon", tmp_path / "out")
    [(command, given)] = ran
    assert signed == tmp_path / "out" / "tarjim-firefox.xpi" and signed.read_bytes() == b"signed"
    assert given["WEB_EXT_API_KEY"] == "user:1:2"
    assert given["WEB_EXT_API_SECRET"] == "not-a-real-secret"
    assert "unlisted" in command and not any("secret" in part for part in command)
    assert "not-a-real-secret" not in capsys.readouterr().out


def test_signing_without_the_keys_says_which_one_is_missing(
        signing: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signing, "kept", lambda _name: "")
    with pytest.raises(SystemExit, match="AMO_JWT_ISSUER"):
        signing.sign(tmp_path / "addon", tmp_path / "out")
