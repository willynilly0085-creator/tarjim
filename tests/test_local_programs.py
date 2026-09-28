from pathlib import Path

import pytest

from tarjim.engines import local_programs


def test_an_installed_ollama_that_is_not_running_is_found_with_its_models(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    program = tmp_path / "ollama.exe"
    program.write_text("")
    library = tmp_path / "models" / "manifests" / "registry.ollama.ai" / "library"
    (library / "qwen2.5").mkdir(parents=True)
    (library / "qwen2.5" / "14b").write_text("{}")
    (library / "gpt-oss").mkdir()
    (library / "gpt-oss" / "20b").write_text("{}")
    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path / "models"))
    monkeypatch.setattr(local_programs.shutil, "which", lambda _name: None)
    monkeypatch.setattr(local_programs, "PLACES", {"ollama": (program,), "jan": ()})
    found = local_programs.installed(running=set())
    assert [(p.id, p.models, p.can_start) for p in found] == [
        ("ollama", ["gpt-oss:20b", "qwen2.5:14b"], True)]
    assert local_programs.installed(running={"ollama"}) == []


def test_only_programs_that_can_serve_are_started(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_programs, "program_of", lambda _server: "C:/jan/Jan.exe")
    assert local_programs.start("jan") is False
    assert local_programs.start("nonsense") is False


def test_a_program_the_person_points_to_is_remembered_only_if_it_is_a_known_ai(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import config

    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    lms = tmp_path / "lms.exe"
    lms.write_text("")
    other = tmp_path / "notepad.exe"
    other.write_text("")
    assert local_programs.remember(f'"{lms}"') == "lmstudio"
    assert local_programs.program_of("lmstudio") == str(lms)
    assert local_programs.remember(str(other)) == ""
    assert local_programs.remember(str(tmp_path / "missing" / "ollama.exe")) == ""


def test_the_search_finds_programs_inside_nested_folders(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import config

    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    deep = tmp_path / "Programs" / "Jan"
    deep.mkdir(parents=True)
    (deep / "Jan.exe").write_text("")
    monkeypatch.setattr(local_programs, "roots", lambda: [tmp_path])
    assert local_programs.search() == ["jan"]
