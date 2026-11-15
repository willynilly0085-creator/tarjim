"""The extension asks for the translation of words selected on a page (tarjim/text.py)."""
from typing import Any

from tarjim.languages import LANGUAGES
from tarjim.server.reasons import classify
from tarjim.text import MOST, Untranslated, translated

Query = dict[str, list[str]]


def refusal(text: str, target: str, other: str) -> tuple[int, dict[str, Any]] | None:
    """Why this is not asked at all. A language is a known code: it is named in the prompt."""
    if not text:
        return 400, {"error": "empty"}
    if len(text) > MOST:
        return 413, {"error": "long", "most": MOST}
    if target not in LANGUAGES or (other and other not in LANGUAGES):
        return 400, {"error": "language"}
    return None


class TextRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def translate_text(self, _query: Query) -> None:
        asked = self.read_json()
        text, other = str(asked.get("text", "")).strip(), str(asked.get("other") or "")
        target = str(asked.get("target") or "ar")
        refused = refusal(text, target, other)
        if refused:
            return self.reply(*refused)
        try:
            said, by = translated(text, target, other)
        except Untranslated as failed:
            cause = failed.__cause__
            code = classify(cause) if isinstance(cause, Exception) else "unknown"
            return self.reply(502, {"error": "failed", "error_code": code})
        self.reply(200, {"translation": said, "by": by})
