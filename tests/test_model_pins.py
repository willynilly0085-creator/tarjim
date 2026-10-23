"""Every model tarjim takes from Hugging Face comes from one fixed commit and loads from that
folder on this computer: a model repository changed or taken over later never reaches anyone."""
import re
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from tarjim import model_pins, pins, tools

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
COMMIT = re.compile(r"[0-9a-f]{40}")


def loaded_repos() -> set[str]:
    from tarjim.asr import ctc, qwen
    from tarjim.dub import clone, separate

    hub = {repo for tool in tools.TOOLS if tool.kind in ("hub", "voice") for repo in tool.sources}
    listening = {qwen.ASR_MODEL, qwen.ALIGNER_MODEL, qwen.EARLIER_ASR, qwen.EARLIER_ALIGNER}
    return {*listening, ctc.Emitter.MODEL, clone.REPO, separate.REPO, *hub}


def test_every_model_tarjim_loads_is_pinned_to_a_commit() -> None:
    assert loaded_repos() == set(model_pins.PINS)
    assert all(COMMIT.fullmatch(pin.revision) for pin in model_pins.PINS.values())


@pytest.mark.parametrize("repo", sorted(model_pins.PINS))
def test_only_settings_tokenizers_and_safe_weights_are_downloaded(repo: str) -> None:
    files = model_pins.PINS[repo].files
    assert "*" not in files and not [f for f in files if f.endswith((".py", ".bin", ".pt"))]
    assert [f for f in files if f.endswith(".pth")] == (
        ["audiovae.pth"] if repo == "openbmb/VoxCPM2" else [])


def hub(monkeypatch: pytest.MonkeyPatch, where: Path) -> list[dict[str, Any]]:
    import huggingface_hub

    asked: list[dict[str, Any]] = []
    monkeypatch.setattr(huggingface_hub, "snapshot_download",
                        lambda repo, **options: asked.append({"repo": repo, **options}) or where)
    return asked


def test_the_pinned_folder_is_looked_up_on_this_computer_only(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked = hub(monkeypatch, tmp_path)
    assert model_pins.folder("openbmb/VoxCPM2") == tmp_path and tools.hub_ready("openbmb/VoxCPM2")
    pin = model_pins.PINS["openbmb/VoxCPM2"]
    assert asked == [{"repo": "openbmb/VoxCPM2", "local_files_only": True,
                      "revision": pin.revision, "allow_patterns": list(pin.files)}] * 2


def test_a_download_takes_the_pinned_commit_and_only_its_named_files(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tarjim.hub_fetch

    asked = hub(monkeypatch, tmp_path)
    fetched: list[tuple[str, ...]] = []
    monkeypatch.setattr(tarjim.hub_fetch, "fetch", lambda *pinned: fetched.append(pinned))
    tools.download(tools.BY_ID["accuracy"])
    assert fetched == [(repo, model_pins.PINS[repo].revision, name, sha)
                       for repo in tools.BY_ID["accuracy"].sources
                       for name, sha in model_pins.PINS[repo].sha256]
    for repo, options in zip(tools.BY_ID["accuracy"].sources, asked, strict=True):
        pin = model_pins.PINS[repo]
        assert options == {"repo": repo, "revision": pin.revision,
                           "allow_patterns": list(pin.files)}


@pytest.fixture
def folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(model_pins, "folder", lambda repo: tmp_path / repo.replace("/", "--"))
    return tmp_path


def test_listening_loads_both_native_models_from_their_pinned_folders(
        folders: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import transformers

    from tarjim.asr import qwen_load

    seen: list[tuple[Any, dict[str, Any]]] = []
    model = types.SimpleNamespace(eval=lambda: "model")
    for name in ("Qwen3ASRForConditionalGeneration", "Qwen3ASRForTokenClassification"):
        monkeypatch.setattr(getattr(transformers, name), "from_pretrained",
                            lambda where, **options: seen.append((where, options)) or model)
    monkeypatch.setattr(transformers.AutoProcessor, "from_pretrained", lambda where: where)
    monkeypatch.setattr(model_pins, "ready", lambda repo: repo.endswith("-hf"))
    asr, aligner = qwen_load.load_pair("cpu")
    assert [where for where, _ in seen] == [folders / "Qwen--Qwen3-ASR-1.7B-hf",
                                            folders / "Qwen--Qwen3-ForcedAligner-0.6B-hf"]
    assert all(options["use_safetensors"] and options["device_map"] == "cpu"
               for _, options in seen)
    assert (asr.processor, aligner.processor) == (seen[0][0], seen[1][0])


def test_word_timing_loads_safetensors_from_its_pinned_folder(
        folders: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import transformers

    from tarjim.asr import ctc

    seen: list[tuple[Any, dict[str, Any]]] = []
    model = types.SimpleNamespace(to=lambda _device: types.SimpleNamespace(eval=lambda: None))
    monkeypatch.setattr(transformers.AutoModelForCTC, "from_pretrained",
                        lambda where, **options: seen.append((where, options)) or model)
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained",
                        lambda where, **options: seen.append((where, options)) or
                        types.SimpleNamespace(get_vocab=dict))
    ctc.Emitter("cpu")
    where = folders / "MahmoudAshraf--mms-300m-1130-forced-aligner"
    assert [found for found, _ in seen] == [where, where] and seen[0][1]["use_safetensors"]


def test_the_own_voice_loads_from_its_pinned_folder(
        folders: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.dub import clone

    seen: list[str] = []

    class VoxCPM:
        @staticmethod
        def from_pretrained(path: str, **_options: Any) -> str:
            seen.append(path)
            return path

    monkeypatch.setitem(sys.modules, "voxcpm", types.SimpleNamespace(VoxCPM=VoxCPM))
    clone.load(optimize=False)
    assert seen == [str(folders / "openbmb--VoxCPM2")]


def test_nothing_in_tarjim_trusts_remote_code_or_loads_a_model_by_name() -> None:
    sources = {path.name: path.read_text(encoding="utf-8") for path in ROOT.rglob("*.py")}
    assert not [name for name, text in sources.items() if "trust_remote_code" in text]
    assert [name for name, text in sources.items() if "snapshot_download(" in text] == [
        "model_pins.py"]
    assert not [name for name, text in sources.items() if "get_model(" in text]


def test_the_package_that_runs_kernels_from_a_model_repository_is_not_installed() -> None:
    assert "kernels" not in pins.parse(pins.FILE.read_text(encoding="utf-8"))
