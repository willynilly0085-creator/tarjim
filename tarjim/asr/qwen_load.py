"""Load the listening pair with Transformers' own Qwen3-ASR classes, from its pinned folders.

The Transformers-native pair (Qwen3-ASR-1.7B-hf, Qwen3-ForcedAligner-0.6B-hf) is used once it is
fully here. Until then a computer that listened with the earlier pair (the qwen-asr package's
format) keeps listening with it: the same weights under other names, so they load into the same
classes with their names mapped and the settings read from the earlier files, and nobody is left
without local listening while the new pair downloads (tarjim/listen_upgrade.py).
"""
import json
from pathlib import Path
from typing import Any

from tarjim.asr.qwen_run import Loaded

ASR_MODEL = "Qwen/Qwen3-ASR-1.7B-hf"
ALIGNER_MODEL = "Qwen/Qwen3-ForcedAligner-0.6B-hf"
EARLIER_ASR = "Qwen/Qwen3-ASR-1.7B"
EARLIER_ALIGNER = "Qwen/Qwen3-ForcedAligner-0.6B"
EARLIER_NAMES = {r"^thinker\.audio_tower\.proj(\d)\.": r"model.multi_modal_projector.linear_\1.",
                 r"^thinker\.audio_tower\.": "model.audio_tower.",
                 r"^thinker\.model\.": "model.language_model.",
                 r"^thinker\.lm_head\.": "lm_head."}
AUDIO = ("d_model", "encoder_layers", "encoder_attention_heads", "encoder_ffn_dim", "num_mel_bins",
         "n_window", "n_window_infer", "conv_chunksize", "downsample_hidden_size", "output_dim",
         "scale_embedding", "activation_function")
TEXT = ("hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
        "num_key_value_heads", "head_dim", "vocab_size", "max_position_embeddings",
        "rms_norm_eps", "hidden_act", "attention_bias", "tie_word_embeddings")
CHUNK_POSITIONS = 13


def options(device: str) -> dict[str, Any]:
    import torch

    from tarjim.device import precision

    return {"dtype": precision(device, torch.bfloat16), "device_map": device,
            "use_safetensors": True}


def classes(aligner: bool) -> Any:
    from transformers import Qwen3ASRForConditionalGeneration, Qwen3ASRForTokenClassification

    return Qwen3ASRForTokenClassification if aligner else Qwen3ASRForConditionalGeneration


def native(repo: str, device: str) -> Loaded:
    from transformers import AutoProcessor

    from tarjim.model_pins import folder

    where = folder(repo)
    model = classes(repo == ALIGNER_MODEL).from_pretrained(where, **options(device))
    return Loaded(model.eval(), AutoProcessor.from_pretrained(where))  # type: ignore[no-untyped-call]


def earlier_config(where: Path, aligner: bool) -> Any:
    from transformers import Qwen3ASRConfig

    saved = json.loads((where / "config.json").read_text(encoding="utf-8"))
    thinker = saved["thinker_config"]
    audio = {key: thinker["audio_config"][key] for key in AUDIO}
    text = {key: thinker["text_config"][key] for key in TEXT}
    text["rope_parameters"] = {"rope_theta": thinker["text_config"]["rope_theta"],
                               "rope_type": "default"}
    extra = {"num_labels": thinker["classify_num"],
             "timestamp_token_id": saved["timestamp_token_id"]} if aligner else {}
    audio["max_position_embeddings"] = CHUNK_POSITIONS
    return Qwen3ASRConfig(audio_config=audio, text_config=text, audio_token_id=thinker[
        "audio_token_id"], tie_word_embeddings=text["tie_word_embeddings"], **extra)


def segment_time(where: Path) -> float:
    saved = json.loads((where / "config.json").read_text(encoding="utf-8"))
    return float(saved.get("timestamp_segment_time", 80))


def earlier_processor(where: Path) -> Any:
    """The earlier tokenizer with the native sound features, which are the same numbers."""
    from transformers import AutoTokenizer, Qwen3ASRFeatureExtractor, Qwen3ASRProcessor

    features = Qwen3ASRFeatureExtractor()  # type: ignore[no-untyped-call]
    return Qwen3ASRProcessor(feature_extractor=features, tokenizer=AutoTokenizer.from_pretrained(
        where), timestamp_segment_time=segment_time(where))


def earlier(repo: str, device: str) -> Loaded:
    from tarjim.model_pins import folder

    where, aligner = folder(repo), repo == EARLIER_ALIGNER
    names = {**EARLIER_NAMES, r"^thinker\.lm_head\.": "score." if aligner else "lm_head."}
    model = classes(aligner).from_pretrained(
        where, config=earlier_config(where, aligner), key_mapping=names, **options(device))
    return Loaded(model.eval(), earlier_processor(where))


def load_pair(device: str) -> tuple[Loaded, Loaded]:
    """The native pair when it is here, else the earlier one; raises OSError when neither is."""
    from tarjim.model_pins import ready

    if ready(ASR_MODEL) and ready(ALIGNER_MODEL):
        return native(ASR_MODEL, device), native(ALIGNER_MODEL, device)
    if ready(EARLIER_ASR) and ready(EARLIER_ALIGNER):
        return earlier(EARLIER_ASR, device), earlier(EARLIER_ALIGNER, device)
    raise FileNotFoundError("the local listening models are not on this computer")
