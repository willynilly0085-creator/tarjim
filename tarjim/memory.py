"""Give the graphics card back when tarjim is idle: models are loaded again on the next job."""
import gc


def release_models() -> None:
    from tarjim.asr.align import shared_aligner
    from tarjim.asr.qwen import shared_engine
    from tarjim.dub.clone import voice_model

    for cached in (shared_engine, shared_aligner, voice_model):
        cached.cache_clear()
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
