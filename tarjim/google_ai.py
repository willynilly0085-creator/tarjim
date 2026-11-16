"""Google's two doors to Gemini, opened with whichever kind of key the person has.

A Gemini API key (AIza…, from AI Studio) has a free daily quota per model. A Vertex AI key (AQ.…,
Vertex express mode) reaches the same models billed to a Google Cloud project, with no daily quota;
it cannot list models (401) and has no Interactions API (404), so voices stay on a Gemini API key.

A Vertex key is asked with no place in the address, and Google answers from the project's own
region. A model that region lacks is a 404 naming the project and the region, and the model is
then asked by its full name at the global location (seen 2026-11-16: the owner's project sat in
europe-west1, Gemini 4 was only at locations/global, and tarjim translated with 3.8 Flash
instead without a word). Only a model the person picked and their region lacks goes there.
"""
import re
from typing import Any

VERTEX_PREFIX = "AQ."
MISSING = 404
PLACE = re.compile(r"`projects/([^/`]+)/locations/(?!global/)[^/`]+/publishers/google/models/")
GLOBAL: dict[str, str] = {}  # a model's full name at the global location, once learnt


def vertex(key: str) -> bool:
    return key.startswith(VERTEX_PREFIX)


def google_client(key: str, options: Any) -> Any:
    from google import genai

    if vertex(key):
        return genai.Client(vertexai=True, api_key=key, http_options=options)
    return genai.Client(api_key=key, http_options=options)


def placed(model: str) -> str:
    """The name Google's library is given for this model."""
    return GLOBAL.get(model, model)


def elsewhere(model: str, error: Exception) -> bool:
    """True once for a model this key's region lacks: it is asked at the global location from
    now on. An AI Studio key's 404 names no project, so it is never taken for one of these."""
    found = PLACE.search(str(error)) if getattr(error, "code", None) == MISSING else None
    if found is None or model in GLOBAL:
        return False
    GLOBAL[model] = f"projects/{found[1]}/locations/global/publishers/google/models/{model}"
    print(f"gemini: {model} is not in this key's region; asked at Google's global location",
          flush=True)
    return True
