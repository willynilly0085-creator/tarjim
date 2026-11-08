"""A kept transcript is used again only when the code and settings that derived it are the ones
running now; otherwise it is derived again from the kept hearing, with no new listening
(2026-11-08: a timing kept by older code was replayed on every run, whatever was fixed since)."""
import json
from pathlib import Path
from typing import Any

import pytest
from test_coverage_flow import SPOKEN, Engine, everything, said, setup

from tarjim import config, hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen import kept
from tarjim.models import Word

STALE = Transcript("English", "stale", [Word("stale", 1.0, 1.5, "S1")])


@pytest.fixture(autouse=True)
def own_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")


def done_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Job, list[int]]:
    """A clip heard and kept; then any new listening is counted."""
    engine = Engine([u for u in SPOKEN if u.start < 160.0])
    job = setup(monkeypatch, tmp_path, engine)
    hearing.transcript_for(job, lambda _stage: None)
    listened: list[int] = []

    def listen(*_args: Any) -> Any:
        listened.append(1)
        raise AssertionError("listened again")

    monkeypatch.setattr(hearing, "listen_video", listen)
    monkeypatch.setattr(hearing, "cloud_listener", lambda _provider: listen)
    return job, listened


def test_the_transcript_carries_the_key_it_was_derived_with(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job, _ = done_once(monkeypatch, tmp_path)
    data = json.loads((job.cache / "transcript.json").read_text(encoding="utf-8"))
    assert data["derive"] == kept.derive_key()
    assert said(hearing.transcript_for(job, lambda _stage: None)) == everything()


def test_the_same_key_reuses_the_kept_transcript(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job, _ = done_once(monkeypatch, tmp_path)
    kept.keep_transcript(job.cache, STALE)
    assert hearing.transcript_for(job, lambda _stage: None).words == STALE.words


@pytest.mark.parametrize("change", ["code", "setting", "old file"])
def test_another_key_derives_it_again_from_the_kept_hearing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], change: str) -> None:
    job, listened = done_once(monkeypatch, tmp_path)
    kept.keep_transcript(job.cache, STALE)
    if change == "code":
        monkeypatch.setattr(kept, "code_key", lambda: "other code")
    elif change == "setting":
        monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "60")
    else:
        STALE.save(job.cache / "transcript.json")  # kept by a release with no key
    assert said(hearing.transcript_for(job, lambda _stage: None)) == everything()
    assert listened == []
    assert "made again from the kept hearing, with no new listening" in capsys.readouterr().out
    data = json.loads((job.cache / "transcript.json").read_text(encoding="utf-8"))
    assert data["derive"] == kept.derive_key()


def test_the_code_key_does_not_depend_on_line_ends(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    keys = []
    for name, ends in (("unix", b"\n"), ("windows", b"\r\n"), ("changed", b"\n#\n")):
        (tmp_path / name / "listen").mkdir(parents=True)
        (tmp_path / name / "listen" / "x.py").write_bytes(b"a = 1" + ends + b"b = 2" + ends)
        monkeypatch.setattr(kept, "ROOT", tmp_path / name)
        monkeypatch.setattr(kept, "DERIVED_FROM", ("listen",))
        keys.append(kept.code_key.__wrapped__())
    assert keys[0] == keys[1] != keys[2]


def test_the_key_covers_the_code_that_derives_a_transcript() -> None:
    """Changed 2026-11-08: the key covered only the files named, so a fix to who a line is given
    to (speakers.py), how words are split (scripts.py), the words themselves (models.py) or the
    local words' language (translate/glossary.py) never reached a clip done before it."""
    names = {p.relative_to(kept.ROOT).as_posix() for p in kept.key_files()}
    assert {"listen/settle.py", "asr/align.py", "segment.py", "dialogue.py", "model_pins.py",
            "speakers.py", "scripts.py", "models.py", "translate/glossary.py"} <= names
    assert "server/app.py" not in names  # what the page runs derives nothing


def key_of(root: Path, files: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> str:
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(kept, "ROOT", root)
    monkeypatch.setattr(kept, "DERIVED_FROM", ("listen",))
    return kept.code_key.__wrapped__()


def test_the_key_follows_what_the_code_imports_at_the_top(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = {"listen/a.py": "from tarjim.helper import split\n\n\ndef f():\n"
                           "    from tarjim.engine import ask\n",
            "helper.py": "from tarjim import deeper\n", "deeper.py": "x = 1\n",
            "engine.py": "y = 1\n"}
    first = key_of(tmp_path / "one", tree, monkeypatch)
    assert key_of(tmp_path / "two", {**tree, "deeper.py": "x = 2\n"}, monkeypatch) != first
    assert key_of(tmp_path / "three", {**tree, "engine.py": "y = 2\n"}, monkeypatch) == first


NOT_DERIVING = {"__init__.py", "config.py", "vault.py", "gemini_client.py", "google_ai.py",
                "engines/catalog.py", "tool_catalog.py", "findings.py", "qa.py"}


def test_the_key_leaves_out_what_changes_every_release_and_derives_nothing() -> None:
    """2026-11-08: `from tarjim import media` took in tarjim/__init__.py, whose version changes
    with every release, and hearing.py's imports took in the settings, the key vault and the
    engines; every release then timed every kept clip again on this computer."""
    names = {p.relative_to(kept.ROOT).as_posix() for p in kept.key_files()}
    assert not names & NOT_DERIVING


def test_a_new_version_alone_keeps_the_key(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tree = {"__init__.py": '__version__ = "1.0.69"\n',
            "listen/a.py": "from tarjim import helper\nfrom tarjim.config import setting\n",
            "helper.py": "x = 1\n", "config.py": "setting = 1\n"}
    first = key_of(tmp_path / "one", tree, monkeypatch)
    assert key_of(tmp_path / "two", {**tree, "__init__.py": '__version__ = "1.0.70"\n'},
                  monkeypatch) == first
    assert key_of(tmp_path / "three", {**tree, "config.py": "setting = 2\n"},
                  monkeypatch) == first
    assert key_of(tmp_path / "four", {**tree, "helper.py": "x = 2\n"}, monkeypatch) != first
