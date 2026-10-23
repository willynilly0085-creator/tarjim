"""Published vulnerabilities the tested versions cannot avoid yet are told to everyone who has an
affected version installed, in their language, and stop being shown once a fixed one is in."""
import json
import re
from pathlib import Path
from typing import Any

import pytest
from packaging.specifiers import SpecifierSet

from tarjim import assistant_setup, known_issues, pins, update

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = sorted(path.stem for path in (ROOT / "tarjim" / "web" / "i18n").glob("*.json"))
KEYS = ("knownIssuesTitle", "knownIssuesLead", "knownIssueModel", "knownIssueUnused",
        "knownIssueOther", "knownIssuesFix", "knownIssuesMore")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def ids() -> set[str]:
    return {entry["id"] for entry in known_issues.entries()}


CLOSED = {"PYSEC-2025-217": ">=5.0.0", "PYSEC-2026-2288": ">=5.0.0", "PYSEC-2026-2289": ">=5.3.0",
          "PYSEC-2026-2290": ">=5.5.0", "PYSEC-2026-3929": ">=5.10.0", "PYSEC-2026-4174": ">=5.9.0"}
SAMPLE = [{"id": "X-1", "package": "transformers", "affected": "<5.0.0", "fixed_by": ">=5.0.0"},
          {"id": "X-2", "package": "transformers", "affected": "<5.10.0", "fixed_by": ">=5.10.0"}]


def test_the_shipped_list_is_the_list_ci_accepts() -> None:
    lines = (ROOT / ".github" / "audit-known.txt").read_text(encoding="utf-8").splitlines()
    accepted = {line.split()[0] for line in lines if line.strip() and not line.startswith("#")}
    assert ids() == accepted


def test_the_six_transformers_advisories_are_closed_by_the_tested_version() -> None:
    """qwen-asr held transformers at 4.57.6; the native Qwen3-ASR classes let it move."""
    (version,) = pins.parse(pins.FILE.read_text(encoding="utf-8"))["transformers"]
    assert all(version in SpecifierSet(fixed) for fixed in CLOSED.values())
    assert not set(CLOSED) & ids()


@pytest.fixture
def sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "known_issues.json"
    file.write_text(json.dumps(SAMPLE), encoding="utf-8")
    monkeypatch.setattr(known_issues, "FILE", file)


@pytest.mark.parametrize("entry", known_issues.entries(), ids=lambda entry: entry["id"])
def test_each_entry_says_what_it_is_what_tarjim_does_and_where_the_fix_comes_from(
        entry: dict[str, Any]) -> None:
    assert all(str(entry.get(key, "")).strip() for key in ("what", "tarjim", "fix", "package"))
    assert entry["reached"] is False and entry["reach"] in ("model", "unused")
    fixed = SpecifierSet(entry["fixed_by"])
    first_fixed = entry["fixed_by"].lstrip(">=")
    assert first_fixed in fixed and not SpecifierSet(entry["affected"]).contains(first_fixed)


@pytest.mark.parametrize(("version", "shown"), [
    ("4.57.6", 2), ("5.0.0", 1), ("5.9.0", 1), ("5.10.0", 0), ("5.20.2", 0)])
@pytest.mark.usefixtures("sample")
def test_only_the_entries_for_the_installed_version_are_shown(version: str, shown: int) -> None:
    found = known_issues.current(lambda name: version if name == "transformers" else "")
    assert len(found) == shown and all(issue["installed"] == version for issue in found)


def test_nothing_is_shown_for_a_library_that_is_not_installed() -> None:
    assert known_issues.current(lambda _name: "") == []


def test_an_entry_the_engine_cannot_read_is_shown_rather_than_hidden(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "known_issues.json"
    file.write_text(json.dumps([{"id": "X-1", "package": "transformers", "affected": "nonsense"}]))
    monkeypatch.setattr(known_issues, "FILE", file)
    assert [issue["id"] for issue in known_issues.current(lambda _name: "4.57.6")] == ["X-1"]


def test_the_closed_accelerate_advisory_no_longer_applies_to_the_tested_version() -> None:
    (version,) = pins.parse(pins.FILE.read_text(encoding="utf-8"))["accelerate"]
    assert not SpecifierSet("<=1.14.0").contains(version)
    assert "PYSEC-2026-3804" not in ids()


@pytest.mark.usefixtures("sample")
def test_the_update_state_carries_the_entries_that_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update, "latest", lambda: "")
    monkeypatch.setattr(known_issues.pins, "installed",
                        lambda name: "4.57.6" if name == "transformers" else "")
    state = update.view()
    assert len(state["known_issues"]) == 2
    assert state["known_issues_details"].endswith("SECURITY.md#known-library-issues")


def test_the_chat_tools_setup_status_passes_them_on(monkeypatch: pytest.MonkeyPatch) -> None:
    import tarjim.assistant_http

    reply = {"known_issues": [{"id": "PYSEC-2026-2289"}], "known_issues_details": "link"}
    monkeypatch.setattr(assistant_setup, "running", lambda: True)
    monkeypatch.setattr(tarjim.assistant_http, "call", lambda path: reply)
    status = assistant_setup.status()
    assert status["engine"] == "running" and status["known_library_issues"] == [
        {"id": "PYSEC-2026-2289"}] and "calmly" in status["known_library_issues_note"]
    reply["known_issues"] = []
    assert "known_library_issues" not in assistant_setup.status()


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_notice_is_written_in_every_language_without_emoji(language: str) -> None:
    words = json.loads((ROOT / "tarjim" / "web" / "i18n" / f"{language}.json").read_text(
        encoding="utf-8"))
    assert all(words.get(key, "").strip() for key in KEYS)
    assert not [key for key in KEYS if EMOJI.search(words[key])]


def test_the_page_shows_the_notice_in_settings() -> None:
    page = (ROOT / "tarjim" / "web" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "tarjim" / "web" / "update.js").read_text(encoding="utf-8")
    assert 'id="known-issues"' in page and all(f'data-t="{key}"' in page for key in (
        "knownIssuesTitle", "knownIssuesLead", "knownIssuesFix", "knownIssuesMore"))
    assert "state.known_issues" in script and "knownIssueModel" in script


@pytest.mark.parametrize("folder", ["", *(f"i18n/{lang}" for lang in LANGUAGES if lang != "en")])
def test_every_readme_and_security_file_tells_them(folder: str) -> None:
    security = (ROOT / folder / "SECURITY.md").read_text(encoding="utf-8")
    readme = (ROOT / folder / "README.md").read_text(encoding="utf-8")
    assert all(advisory in security for advisory in ids())
    assert "](SECURITY.md" in readme and "--overrides tarjim/overrides.txt" in readme
