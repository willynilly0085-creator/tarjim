"""Google's two doors to Gemini, opened with whichever kind of key the person has.

A Gemini API key (AIza…, from AI Studio) has a free daily quota per model. A Vertex AI key (AQ.…,
Vertex express mode) reaches the same models billed to a Google Cloud project, with no daily quota;
it cannot list models (401) and has no Interactions API (404), so voices stay on a Gemini API key.
"""
from typing import Any

VERTEX_PREFIX = "AQ."


def vertex(key: str) -> bool:
    return key.startswith(VERTEX_PREFIX)


def google_client(key: str, options: Any) -> Any:
    from google import genai

    if vertex(key):
        return genai.Client(vertexai=True, api_key=key, http_options=options)
    return genai.Client(api_key=key, http_options=options)
