"""Give the graphics card back: when tarjim is idle, and before the dubbing voice loads.

A job listens, then translates, then dubs, one after the other. Without freeing the earlier models,
a local-listening, local-translation, own-voice job would hold all three on the card at once
(about 18 GB); freeing them first keeps the peak at the largest single model (about 6 GB).
"""
import gc

UNLOAD_SECONDS = 5


def empty_card() -> None:
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_listening() -> None:
    from tarjim.asr.align import shared_aligner
    from tarjim.asr.qwen import shared_engine

    shared_engine.cache_clear()
    shared_aligner.cache_clear()


def release_local_translator() -> None:
    import requests

    from tarjim.config import setting
    from tarjim.engines.choice import LOCAL, chosen
    from tarjim.engines.ollama import base_url

    model = setting("local_model")
    if chosen("translate") != LOCAL or not model or setting("local_server") not in ("", "ollama"):
        return
    try:
        requests.post(f"{base_url()}/api/generate", json={"model": model, "keep_alive": 0},
                      timeout=UNLOAD_SECONDS)
    except requests.RequestException:
        return


def free_for_voice() -> None:
    release_listening()
    release_local_translator()
    empty_card()


def free_for_listening() -> None:
    """A new job starts by listening: the voice of the job before it leaves the card first."""
    from tarjim.dub.clone import voice_model

    if voice_model.cache_info().currsize:
        voice_model.cache_clear()
        empty_card()


def release_models() -> None:
    from tarjim.dub.clone import voice_model

    release_listening()
    voice_model.cache_clear()
    empty_card()
