"""Any provider's model list, shaped the same way for the page: named like the provider's own app,
newest first with older versions under "more models", and the lightest model suggested because
translating subtitles needs little from a model.

A row is (id, name the provider gives or "", the provider's short description or "").
"""
import re

LIGHT = ("haiku", "flash", "mini", "lite", "small", "instant", "nano", "turbo", "luna", "chat",
         "affordable", "fast", "efficient")
NOT_TEXT = ("embed", "tts", "audio", "image", "imagen", "whisper", "dall-e", "moderation",
            "realtime", "transcribe", "search", "guard", "rerank", "speech", "veo", "live",
            "computer-use", "codex-auto")
OLDER = ("older", "legacy", "previous", "deprecated")
WORDS = {"gpt": "GPT", "deepseek": "DeepSeek", "openai": "OpenAI", "qwen": "Qwen", "glm": "GLM",
         "llama": "Llama", "xai": "xAI", "ai": "AI"}
NUMBERS = re.compile(r"\d+(?:\.\d+)?")
SHORT_NUMBER = re.compile(r"\d{1,2}")
Row = tuple[str, str, str]
Model = dict[str, str]


def word(token: str) -> str:
    if token in WORDS:
        return WORDS[token]
    if re.fullmatch(r"v\d+(\.\d+)?", token):
        return token.upper()
    return token if token[:1].isdigit() else token.capitalize()


def tokens_of(model_id: str) -> list[str]:
    """Split an id into words, joining "5-5" back into the version "5.5"."""
    tokens: list[str] = []
    for token in model_id.rsplit("/", maxsplit=1)[-1].split("-"):
        if tokens and SHORT_NUMBER.fullmatch(token) and SHORT_NUMBER.fullmatch(tokens[-1]):
            tokens[-1] += f".{token}"
        elif token:
            tokens.append(token)
    return tokens


def pretty(model_id: str) -> str:
    return " ".join(word(token) for token in tokens_of(model_id))


def version(model_id: str) -> tuple[float, ...]:
    return tuple(float(n) for n in NUMBERS.findall(model_id))


def family(model_id: str) -> str:
    return NUMBERS.sub("", model_id).replace("..", ".").strip("-.")


def text_model(row: Row) -> bool:
    return not any(word in row[0].lower() for word in NOT_TEXT)


def light(row: Row) -> bool:
    words = set(re.split(r"[^a-z0-9]+", f"{row[0]} {row[1]} {row[2]}".lower()))
    return any(word in words for word in LIGHT)


def groups(rows: list[Row], keep_order: bool) -> dict[str, str]:
    if keep_order:
        return {row[0]: "more" if any(w in row[2].lower() for w in OLDER) else "latest"
                for row in rows}
    seen: set[str] = set()
    placed = {}
    for row in rows:
        placed[row[0]] = "more" if family(row[0]) in seen else "latest"
        seen.add(family(row[0]))
    return placed


def describe(rows: list[Row], keep_order: bool = False) -> list[Model]:
    kept = [row for row in rows if text_model(row)]
    if not keep_order:
        kept.sort(key=lambda row: version(row[0]), reverse=True)
    placed = groups(kept, keep_order)
    fitting = [row for row in kept if placed[row[0]] == "latest" and light(row)]
    free = [row for row in fitting if "free" in re.split(r"[^a-z0-9]+", row[0].lower())]
    suggested = (free or fitting or [("", "", "")])[0][0]
    ordered = [row for row in kept if placed[row[0]] == "latest"]
    ordered += [row for row in kept if placed[row[0]] == "more"]
    return [{"id": row[0], "name": row[1] or pretty(row[0]), "group": placed[row[0]],
             "suggested": "yes" if row[0] == suggested else ""} for row in ordered]
