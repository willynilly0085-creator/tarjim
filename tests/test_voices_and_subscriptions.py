from pathlib import sys
from typing import Any

import Path
import pytest

from tarjim.dub import gemini_voice
from tarjim.dub.lines import Line
from tarjim.dub.script import prompt
from tarjim.dub.split import line_ends
from tarjim.engines import subscription


def test_seams_fall_between_the_last_and_first_word_of_neighbouring_lines() -> None:
    words = [(0.0, 0.4), (0.5, 0.9), (1.5, 1.9), (2.0, 2.2), (3.0, 3.4)]
    assert line_ends(words, [2, 2, 1]) == [1.2, 2.6]


def test_each_speaker_is_recorded_in_as_few_requests_as_possible() -> None:
    lines = [Line(0, 1, "A", "one"), Line(1, 2, "B", "two"), Line(2, 3, "A", "three")]
    assert gemini_voice.batches(lines) == [[0, 2], [1]]


def test_long_speakers_are_split_into_several_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_voice, "BATCH_CHARS", 6)
    lines = [Line(0, 1, "A", "abcd"), Line(1, 2, "A", "efgh")]
    assert gemini_voice.batches(lines) == [[0], [1]]


def test_voice_script_takes_names_from_the_original_and_vowels_only_when_asked() -> None:
    lines = [Line(0, 4, "A", "مع بوكتس فلو", "With Pocketflow")]
    full = prompt(lines, "Arabic", "saudi", full_vowels=True)
    light = prompt(lines, "Arabic", "saudi", full_vowels=False)
    assert "original: With Pocketflow" in full and "ORIGINAL" in full
    assert "every word" in full and "every word" not in light
    assert "diacritics" not in prompt(lines, "French", "", full_vowels=True)


def test_codex_schema_is_made_strict() -> None:
    shape = subscription.strict({"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["id"]}})
    assert shape["items"]["additionalProperties"] is False
    assert shape["items"]["required"] == ["id", "text"]


@pytest.mark.skipif(sys.platform != "win32", reason="npm writes .cmd launchers on Windows only")
def test_npm_launchers_run_the_real_program_not_cmd(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    shim = tmp_path / "codex.cmd"
    shim.write_text('@echo off\r\n"%_prog%"  "%dp0%\\node_modules\\codex\\bin\\codex.js" %*\r\n')
    found: dict[str, Any] = {"codex.cmd": str(shim), "node": "C:/node.exe"}
    monkeypatch.setattr(subscription.shutil, "which", found.get)
    assert subscription.launcher("codex") == ["C:/node.exe",
                                              str(tmp_path / "node_modules/codex/bin/codex.js")]
    assert subscription.launcher("claude") == []


def test_codex_tries_the_remembered_model_first(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "models_cache.json").write_text(
        '{"models": [{"slug": "big"}, {"slug": "gpt-reserve"}, {"slug": "small"}]}')
    monkeypatch.setattr(subscription.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(subscription, "setting", lambda name: "small")
    assert subscription.codex_models() == ["small", "big"]
