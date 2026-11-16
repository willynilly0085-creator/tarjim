"""The engine and model that translate selected text, apart from the videos'.

Asked for by the owner on 2026-11-16: his videos stay on a strong model that takes its time,
while a selection wants its answer in a second or two. Saved as text_provider, text_model and
text_server (for an AI program on this computer). Nothing saved means automatic: tarjim asks
the engine that answers soonest (choice.soonest). A picked engine is asked as picked, and
`over` gives the settings the translation then runs under (config.using), so every engine reads
its model the way it does for a video, with no second code path.
"""
import re
from typing import Any

from tarjim.config import save, setting
from tarjim.engines.catalog import BY_ID
from tarjim.engines.choice import LOCAL

MODEL_NAME = re.compile(r"^[\w.:/@+\[\]-]{1,120}$")
KEPT = ("text_provider", "text_model", "text_server")


def server() -> str:
    from tarjim.engines.local_servers import BY_ID as SERVERS
    from tarjim.engines.local_servers import chosen_server

    picked = setting("text_server")
    return picked if picked in SERVERS else chosen_server()


def picked() -> str:
    """The engine the person picked for text; empty when tarjim picks, or it is not known."""
    provider = setting("text_provider")
    return provider if provider == LOCAL or provider in BY_ID else ""


def over() -> dict[str, str]:
    """The settings a selection is translated under; none when tarjim picks the engine."""
    provider, model = picked(), setting("text_model")
    if not provider:
        return {}
    if provider == LOCAL:
        return {"translate_provider": LOCAL, "local_server": server(),
                **({"local_model": model} if model else {})}
    return {"translate_provider": provider,
            **({BY_ID[provider].model_name: model} if model else {})}


def view() -> dict[str, str]:
    """The choice for the page: ids, and the names a person reads."""
    from tarjim.engines.local_servers import BY_ID as SERVERS
    from tarjim.engines.model_catalog import pretty

    provider, model = picked(), setting("text_model")
    if not provider:
        return {"provider": "", "model": "", "server": "", "name": "", "label": ""}
    local = provider == LOCAL
    name = SERVERS[server()][0] if local else BY_ID[provider].name
    return {"provider": provider, "model": model, "server": server() if local else "",
            "name": name, "label": pretty(model) if model else ""}


def works(provider: str, local_server: str) -> bool:
    from tarjim.server.translator_check import translator_works

    return translator_works(provider, local_server)


def remember(data: dict[str, Any]) -> bool:
    """Save the choice; an empty provider goes back to automatic. False when it cannot work
    now, so the page never keeps a choice that would only fail on the next selection."""
    provider, model = str(data.get("provider") or ""), str(data.get("model") or "")
    local_server = str(data.get("server") or "ollama") if provider == LOCAL else ""
    known = provider == LOCAL or provider in BY_ID
    if provider and not (known and works(provider, local_server)):
        return False
    if model and not MODEL_NAME.match(model):
        return False
    for name, value in zip(KEPT, (provider, model if provider else "", local_server),
                           strict=True):
        save(name, value)
    return True
