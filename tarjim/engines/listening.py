"""What each way of hearing the speech needs on this computer, for the setup page.

Local listening runs Qwen3-ASR on the device: it detects the spoken language by itself and needs
its model downloaded once. Gemini and OpenAI hear in the cloud and need a key.
"""
from typing import Any

from tarjim.engines.catalog import BY_ID
from tarjim.engines.choice import has_key

CLOUD = ("gemini", "openai")


def local_status() -> dict[str, Any]:
    from tarjim.system import graphics
    from tarjim.tools import BY_ID as TOOLS
    from tarjim.tools import installed

    missing = [tool for tool in (TOOLS["accuracy"],) if not installed(tool)]
    card = graphics()
    return {"id": "local", "ready": not missing,
            "download_gb": round(sum(tool.size_gb for tool in missing), 1),
            "gpu": bool(card and card.get("usable"))}


def listening_overview() -> list[dict[str, Any]]:
    cloud = [{"id": provider, "name": BY_ID[provider].name, "ready": has_key(provider),
              "download_gb": 0, "gpu": False} for provider in CLOUD]
    return [local_status(), *cloud]
