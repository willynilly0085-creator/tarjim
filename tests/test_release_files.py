"""A release carries the Mac and Linux installer and the Windows folder, so GitHub counts them."""
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_the_release_files_are_made_from_the_tag(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("release_files",
                                                  ROOT / "scripts" / "release_files.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        script, archive = module.make("HEAD", tmp_path)
    except Exception as error:  # a copy without its history (some test machines)
        pytest.skip(f"no git history here: {error}")
    text = script.read_bytes()
    assert text.startswith(b"#!/usr/bin/env bash") and b"\r" not in text
    names = zipfile.ZipFile(archive).namelist()
    assert "tarjim/install.cmd" in names and "tarjim/scripts/windows/install.ps1" in names
