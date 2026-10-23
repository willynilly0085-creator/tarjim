"""The listening pair loads with Transformers' own classes from its pinned folders: the native
pair once both are here, else the earlier pair's weights with their names mapped, else nothing."""
import json
import types
from pathlib import Path
from typing import Any

import pytest

from tarjim.asr import qwen_load


def earlier_folder(tmp_path: Path, aligner: bool) -> Path:
    audio = {key: 1 for key in qwen_load.AUDIO} | {"activation_function": "gelu",
                                                   "scale_embedding": False}
    text = {key: 2 for key in qwen_load.TEXT} | {"rope_theta": 1000000, "hidden_act": "silu",
                                                 "rms_norm_eps": 1e-6,
                                                 "attention_bias": False,
                                                 "tie_word_embeddings": not aligner}
    thinker = {"audio_config": audio, "text_config": text, "audio_token_id": 151676,
               **({"classify_num": 5000} if aligner else {})}
    saved = {"thinker_config": thinker, **({"timestamp_token_id": 151705,
                                            "timestamp_segment_time": 80} if aligner else {})}
    (tmp_path / "config.json").write_text(json.dumps(saved), encoding="utf-8")
    return tmp_path


def test_the_earlier_models_load_into_the_same_classes_with_their_names_mapped(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import transformers

    from tarjim import model_pins
    folder = earlier_folder(tmp_path, aligner=True)
    seen: dict[str, Any] = {}
    monkeypatch.setattr(model_pins, "folder", lambda _repo: folder)
    monkeypatch.setattr(transformers.Qwen3ASRForTokenClassification, "from_pretrained",
                        lambda where, **options: seen.update(where=where, **options) or
                        types.SimpleNamespace(eval=lambda: "aligner"))
    monkeypatch.setattr(qwen_load, "earlier_processor", lambda where: where)
    loaded = qwen_load.earlier(qwen_load.EARLIER_ALIGNER, "cpu")
    assert seen["where"] == folder and seen["use_safetensors"]
    assert seen["key_mapping"][r"^thinker\.lm_head\."] == "score."
    assert seen["key_mapping"][r"^thinker\.audio_tower\.proj(\d)\."] == (
        r"model.multi_modal_projector.linear_\1.")
    config = seen["config"]
    assert config.num_labels == 5000 and config.timestamp_token_id == 151705 and (
        config.text_config.rope_parameters["rope_type"] == "default")
    assert loaded.processor == folder and qwen_load.segment_time(folder) == 80.0


@pytest.mark.parametrize(("ready", "used"), [
    ({"Qwen/Qwen3-ASR-1.7B-hf", "Qwen/Qwen3-ForcedAligner-0.6B-hf", "Qwen/Qwen3-ASR-1.7B",
      "Qwen/Qwen3-ForcedAligner-0.6B"}, "native"),
    ({"Qwen/Qwen3-ASR-1.7B-hf", "Qwen/Qwen3-ASR-1.7B", "Qwen/Qwen3-ForcedAligner-0.6B"}, "earlier"),
])
def test_the_native_pair_is_used_once_both_are_here_else_the_earlier_one(
        monkeypatch: pytest.MonkeyPatch, ready: set[str], used: str) -> None:
    from tarjim import model_pins

    monkeypatch.setattr(model_pins, "ready", lambda repo: repo in ready)
    monkeypatch.setattr(qwen_load, "native", lambda repo, _device: ("native", repo))
    monkeypatch.setattr(qwen_load, "earlier", lambda repo, _device: ("earlier", repo))
    assert {kind for kind, _ in qwen_load.load_pair("cpu")} == {used}


def test_without_either_pair_the_engine_says_listening_is_not_installed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import model_pins

    monkeypatch.setattr(model_pins, "ready", lambda _repo: False)
    with pytest.raises(OSError, match="not on this computer"):
        qwen_load.load_pair("cpu")
