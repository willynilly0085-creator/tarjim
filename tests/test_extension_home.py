"""The extension is loaded from one short folder that stays put across updates."""
import os
from pathlib import Path

import pytest

from tarjim import config, extension_home


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path / "home")
    return tmp_path / "home" / "extension"


def test_the_extension_is_copied_to_a_short_folder_in_tarjims_home(home: Path) -> None:
    assert extension_home.extension_folder() == str(home)
    assert (home / "manifest.json").read_bytes() == (
        extension_home.PACKAGED / "manifest.json").read_bytes()
    assert extension_home.current(home)


def test_an_update_refreshes_the_copy_and_drops_files_it_no_longer_ships(home: Path) -> None:
    extension_home.extension_folder()
    stale = home / "retired.js"  # a file the extension no longer ships
    stale.write_text("old", encoding="utf-8")
    changed = home / "background.js"
    changed.write_text("old", encoding="utf-8")
    os.utime(changed, (0, 0))
    assert not extension_home.current(home)
    extension_home.extension_folder()
    assert not stale.exists()
    assert changed.read_bytes() == (extension_home.PACKAGED / "background.js").read_bytes()


def test_asking_for_the_update_state_refreshes_the_folder_first(home: Path) -> None:
    """The extension reloads when the engine reports a newer version; the folder it reloads from
    must already hold it, even when tarjim's files changed while the engine was running."""
    from tarjim.server.update_routes import UpdateRoutes

    extension_home.extension_folder()
    manifest = home / "manifest.json"
    manifest.write_text('{"version": "0.0.1"}', encoding="utf-8")
    replies: list[int] = []
    routes = UpdateRoutes()
    routes.reply = lambda code, _payload: replies.append(code)  # type: ignore[method-assign]
    routes.update_state({})
    assert replies == [200]
    assert manifest.read_bytes() == (extension_home.PACKAGED / "manifest.json").read_bytes()


def test_firefox_gets_the_same_files_with_a_manifest_it_can_read(home: Path) -> None:
    """2026-11-12: Firefox runs no service worker and an add-on there names itself."""
    import json

    folder = Path(extension_home.firefox_folder())
    assert folder == home.parent / "extension-firefox"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["background"] == {"scripts": ["background.js"], "type": "module"}
    gecko = manifest["browser_specific_settings"]["gecko"]
    assert gecko["id"] == extension_home.GECKO_ID and gecko["strict_min_version"] == "128.0"
    assert gecko["data_collection_permissions"] == {"required": ["none"]}
    packaged = json.loads((extension_home.PACKAGED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == packaged["version"] and "service_worker" in packaged["background"]
    assert (folder / "jobs.js").read_bytes() == (extension_home.PACKAGED / "jobs.js").read_bytes()
    stale = folder / "retired.js"
    stale.write_text("old", encoding="utf-8")
    extension_home.firefox_folder()  # an update drops what it no longer ships, here too
    assert not stale.exists() and extension_home.same_but_manifest(folder)
