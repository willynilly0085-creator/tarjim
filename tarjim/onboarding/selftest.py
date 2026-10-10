"""The last setup step: translate one short sentence with the engine the person chose, so they see
with their own eyes that the connection works before they start."""
from typing import Any

from tarjim.server.evidence import evidence

SAMPLE = "Welcome to tarjim. Every video, in your language."
SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
MAX_ERROR = 200
NAME_IN_ARABIC = "ترجم"


def selftest(language: str) -> dict[str, Any]:
    from tarjim.engines.choice import asker, chosen
    from tarjim.languages import LANGUAGES
    from tarjim.translate.glossary import current, instructions

    target = LANGUAGES[language].name if language in LANGUAGES else "Arabic"
    own_name = (("tarjim", NAME_IN_ARABIC if language == "ar" else "tarjim"),)
    prompt = (f"Translate this sentence into {target}."
              f"{instructions(own_name + current(language))}\n\n{SAMPLE}")
    try:
        answer = asker(chosen("translate")).ask(prompt, None, SCHEMA)
    except Exception as error:
        return {"ok": False, "error": evidence(str(error))[:MAX_ERROR]}
    text = str(answer.get("text", "")) if isinstance(answer, dict) else str(answer or "")
    return {"ok": bool(text.strip()), "text": text.strip()}
