"""Carry out the plan the person approved: save the choices, start the AI program on this computer
if it is needed, and start every download in the background."""
from typing import Any, Protocol

TOOLS = ("ffmpeg", "timing", "accuracy", "dubbing", "local_translation")


class Starts(Protocol):
    def start(self, tool_id: str, accepted: bool = False) -> str: ...


def choose(choice: dict[str, Any]) -> bool:
    from tarjim.server.connections import remember_choice

    translate, listen = choice.get("translate", {}), choice.get("listen", {})
    if translate.get("provider") == "local":
        from tarjim.engines.local_programs import start

        start(str(translate.get("server", "")))
    return remember_choice({"provider": translate.get("provider", ""),
                            "model": translate.get("model", ""),
                            "server": translate.get("server", "ollama"),
                            "listen": listen.get("provider", "")})


def apply(choice: dict[str, Any], shelf: Starts) -> dict[str, Any]:
    saved = choose(choice)
    accepted = set(choice.get("accept", []))
    started = {tool: shelf.start(tool, tool in accepted)
               for tool in choice.get("downloads", []) if tool in TOOLS}
    return {"saved": saved, "downloads": started}
